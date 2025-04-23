import logging
import uuid
from typing import Optional, Type, Callable, Awaitable, Any, TypeVar, Union
from backend_common.common_endpoints import app
import stripe
from fastapi import (
    Body,
    HTTPException,
    status,
    FastAPI,
    Request,
    Depends,
    BackgroundTasks,
    UploadFile,
    File,
    Form,
)
from fetch_dataset_llm import process_llm_query
import json
from backend_common.background import set_background_tasks
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from pydantic import ValidationError
import asyncio
from backend_common.dtypes.auth_dtypes import (
    ReqChangeEmail,
    ReqChangePassword,
    ReqConfirmReset,
    ReqCreateFirebaseUser,
    ReqResetPassword,
    ReqUserId,
    ReqUserLogin,
    ReqUserProfile,
    ReqRefreshToken,
    ReqCreateUserProfile,
    UserProfileSettings
)

from all_types.myapi_dtypes import (
    ReqModel,
    ReqFetchDataset,
    ReqPrdcerLyrMapData,
    # ReqNearestRoute,
    ReqCostEstimate,
    ReqSavePrdcerCtlg,
    ReqDeletePrdcerCtlg,
    ReqGradientColorBasedOnZone,
    ReqStreeViewCheck,
    ReqSavePrdcerLyer,
    ReqFetchCtlgLyrs,
    ReqCityCountry,
    ReqDeletePrdcerLayer,
    ReqLLMFetchDataset,
    ReqPrompt,
    ValidationResult,
    ReqFilter, 
    Req_src_distination
)
from backend_common.request_processor import request_handling
from backend_common.auth import (
    create_firebase_user,
    login_user,
    my_verify_id_token,
    reset_password,
    confirm_reset,
    change_password,
    refresh_id_token,
    change_email,
    db,
    JWTBearer,
    create_user_profile
)

from all_types.response_dtypes import (
    ResModel,
    ResFetchDataset,
    ResCostEstimate,
    ResAddPaymentMethod,
    ResGradientColorBasedOnZone,
    ResGetPaymentMethods,
    ResLyrMapData,
    card_metadata,
    CityData,
    NearestPointRouteResponse,
    UserCatalogInfo,
    LayerInfo,
    ResLLMFetchDataset,
    Res_src_distination
)

from google_api_connector import check_street_view_availability
from config_factory import CONF
from cost_calculator import calculate_cost
from data_fetcher import (
    fetch_country_city_data,
    fetch_catlog_collection,
    fetch_layer_collection,
    save_lyr,
    delete_layer,
    aquire_user_lyrs,
    fetch_lyr_map_data,
    save_prdcer_ctlg,
    delete_prdcer_ctlg,
    fetch_prdcer_ctlgs,
    fetch_ctlg_lyrs,
    poi_categories,
    save_draft_catalog,
    fetch_gradient_colors,
    get_user_profile,
    # fetch_nearest_points_Gmap,
    fetch_dataset,
    load_area_intelligence_categories,
    update_profile,
    load_distance_drive_time_polygon
    
)
from backend_common.dtypes.stripe_dtypes import (
    ProductReq,
    ProductRes,
    CustomerReq,
    CustomerRes,
    SubscriptionCreateReq,
    SubscriptionUpdateReq,
    SubscriptionRes,
    PaymentMethodReq,
    PaymentMethodUpdateReq,
    PaymentMethodRes,
    PaymentMethodAttachReq,
    TopUpWalletReq,
    DeductWalletReq
)
from backend_common.database import Database
from backend_common.logging_wrapper import log_and_validate
from backend_common.stripe_backend import (
    create_stripe_product,
    update_stripe_product,
    delete_stripe_product,
    list_stripe_products,
    create_stripe_customer,
    update_customer,
    list_customers,
    fetch_customer,
    create_subscription,
    update_subscription,
    deactivate_subscription,
    create_payment_method,
    update_payment_method,
    attach_payment_method,
    delete_payment_method,
    list_payment_methods,
    set_default_payment_method,
    testing_create_card_payment_source,
    top_up_wallet,
    fetch_wallet,
    deduct_from_wallet
)
from recoler_filter import (process_color_based_on_agent,process_color_based_on,filter_based_on)

# TODO: Add stripe secret key

stripe.api_key = CONF.stripe_api_key
logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)
U = TypeVar("U", bound=BaseModel)


def create_formatted_example(model_class):
    """Create a formatted JSON example string"""
    schema = model_class.model_json_schema()

    def get_default_value(field_type):
        if field_type == "string":
            return "string"
        elif field_type == "integer" or field_type == "number":
            return 0
        elif field_type == "array":
            return []
        elif field_type == "object":
            return {}
        return None

    def create_example_from_properties(properties, required_fields):
        example = {}
        for field_name, field_info in properties.items():
            if field_info.get("type") == "array" and "items" in field_info:
                items = field_info["items"]
                if "$ref" in items:
                    ref_name = items["$ref"].split("/")[-1]
                    ref_schema = schema["$defs"][ref_name]
                    example[field_name] = [
                        create_example_from_properties(
                            ref_schema["properties"], ref_schema.get("required", [])
                        )
                    ]
                else:
                    example[field_name] = [get_default_value(items["type"])]
            else:
                example[field_name] = get_default_value(
                    field_info.get("type", "string")
                )
        return example

    example = {
        "message": "string",
        "request_info": {},
        "request_body": create_example_from_properties(
            schema["properties"], schema.get("required", [])
        ),
    }

    return example


# app = FastAPI()

# Enable CORS
origins = [CONF.enable_CORS_url]

app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])
app.add_middleware(
    CORSMiddleware,
    # allow_origins=origins,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def background_tasks_middleware(request, call_next):
    background_tasks = BackgroundTasks()
    set_background_tasks(background_tasks)
    response = await call_next(request)
    response.background = background_tasks
    return response


@app.on_event("startup")
async def startup_event():
    await Database.create_pool()
    await db.initialize_all()


@app.on_event("shutdown")
async def shutdown_event():
    await Database.close_pool()
    # Run cleanup in a thread to not block
    await asyncio.get_event_loop().run_in_executor(None, db.cleanup)
    # Wait a moment to ensure threads are cleaned up
    await asyncio.sleep(1)


@app.get(CONF.fetch_acknowlg_id, response_model=ResModel[str])
async def fetch_acknowlg_id():
    response = await request_handling(None, None, ResModel[str], None, wrap_output=True)
    return response


@app.get(CONF.catlog_collection, response_model=ResModel[list[card_metadata]])
async def catlog_collection():
    response = await request_handling(
        None,
        None,
        ResModel[list[card_metadata]],
        fetch_catlog_collection,
        wrap_output=True,
    )
    return response


@app.get(CONF.layer_collection, response_model=ResModel[list[card_metadata]])
async def layer_collection():
    response = await request_handling(
        None,
        None,
        ResModel[list[card_metadata]],
        fetch_layer_collection,
        wrap_output=True,
    )
    return response


@app.get(CONF.country_city, response_model=ResModel[dict[str, list[CityData]]])
async def country_city():
    response = await request_handling(
        None,
        None,
        ResModel[dict[str, list[CityData]]],
        fetch_country_city_data,
        wrap_output=True,
    )
    return response


@app.get(CONF.nearby_categories, response_model=ResModel[dict[str, list[str]]])
async def ep_city_categories(
    # req: ReqModel[ReqCityCountry]
):
    response = await request_handling(
        "",
        "",
        # req.request_body,
        # ReqCityCountry,
        ResModel[dict[str, list[str]]],
        poi_categories,
        wrap_output=True,
    )
    return response


@app.get(CONF.nearby_categories, response_model=ResModel[dict[str, list[str]]])
async def ep_load_area_intelligence_categories(
    # req: ReqModel[ReqCityCountry]
):
    response = await request_handling(
        "",
        "",
        # req.request_body,
        # ReqCityCountry,
        ResModel[dict[str, list[str]]],
        load_area_intelligence_categories,
        wrap_output=True,
    )
    return response


@app.post(
    CONF.fetch_dataset,
    response_model=ResModel[ResFetchDataset],
    dependencies=[Depends(JWTBearer())],
)
async def fetch_dataset_ep(req: ReqModel[ReqFetchDataset], request: Request):
    response = await request_handling(
        req.request_body,
        ReqFetchDataset,
        ResModel[ResFetchDataset],
        fetch_dataset,
        wrap_output=True,
    )
    return response

@app.post(
    CONF.process_llm_query,
    response_model=ResModel[ResLLMFetchDataset],
    dependencies=[Depends(JWTBearer())],
)
async def process_llm_query_ep(req: ReqModel[ReqLLMFetchDataset], request: Request):
    response = await request_handling(
        req.request_body,
        ReqLLMFetchDataset,
        ResModel[ResLLMFetchDataset],
        process_llm_query,
        wrap_output=True,
    )
    return response


@app.post(
    CONF.save_layer, response_model=ResModel[str], dependencies=[Depends(JWTBearer())]
)
async def save_layer_ep(req: ReqModel[ReqSavePrdcerLyer], request: Request):
    response = await request_handling(
        req.request_body, ReqSavePrdcerLyer, ResModel[str], save_lyr, wrap_output=True
    )
    return response


@app.delete(
    CONF.delete_layer,  
    response_model=ResModel[str],
    dependencies=[Depends(JWTBearer())]
)
async def delete_layer_ep(req: ReqModel[ReqDeletePrdcerLayer], request: Request):
    response = await request_handling(
        req.request_body, ReqDeletePrdcerLayer, ResModel[str], delete_layer, wrap_output=True
    )
    return response



@app.post(CONF.user_layers, response_model=ResModel[list[LayerInfo]])
async def user_layers(req: ReqModel[ReqUserId]):
    response = await request_handling(
        req.request_body,
        ReqUserId,
        ResModel[list[LayerInfo]],
        aquire_user_lyrs,
        wrap_output=True,
    )
    return response





@app.post(CONF.prdcer_lyr_map_data, response_model=ResModel[ResLyrMapData])
async def prdcer_lyr_map_data(req: ReqModel[ReqPrdcerLyrMapData]):
    response = await request_handling(
        req.request_body,
        ReqPrdcerLyrMapData,
        ResModel[ResLyrMapData],
        fetch_lyr_map_data,
        wrap_output=True,
    )
    return response


# @app.post(
#     CONF.nearest_lyr_map_data,
#     description="Get Nearest Point",
#     response_model=ResModel[list[NearestPointRouteResponse]],
# )
# async def calculate_nearest_route(req: ReqModel[ReqNearestRoute]):
#     response = await request_handling(
#         req.request_body,
#         ReqNearestRoute,
#         ResModel[list[NearestPointRouteResponse]],
#         fetch_nearest_points_Gmap,
#         wrap_output=True,
#     )
#     return response


@app.post(
    CONF.save_producer_catalog,
    response_model=ResModel[str],
    dependencies=[Depends(JWTBearer())],
)
async def ep_save_producer_catalog(
    req: Union[str, dict[str, Any]] = Form(
        ...,
        description=(
            "Expected request format:\n\n"
            "```json\n"
            f"{json.dumps(create_formatted_example(ReqSavePrdcerCtlg), indent=2)}\n"
            "```"
        ),
        example=create_formatted_example(ReqSavePrdcerCtlg),
    ),
    image: Optional[UploadFile] = File(None),
):
    if isinstance(req, str):
        req = json.loads(req)
    req_model = ReqModel(**req)
    req_model.request_body["image"] = image

    response = await request_handling(
        req_model.request_body,
        None,
        ResModel[str],
        save_prdcer_ctlg,
        wrap_output=True,
    )
    return response

@app.delete(
    CONF.delete_producer_catalog,  
    response_model=ResModel[str],
    dependencies=[Depends(JWTBearer())]
)
async def ep_delete_producer_catalog(req: ReqModel[ReqDeletePrdcerCtlg], request: Request):
    response = await request_handling(
        req.request_body, ReqDeletePrdcerCtlg, ResModel[str], delete_prdcer_ctlg, wrap_output=True
    )
    return response



@app.post(CONF.user_catalogs, response_model=ResModel[list[UserCatalogInfo]])
async def user_catalogs(req: ReqModel[ReqUserId]):
    response = await request_handling(
        req.request_body,
        ReqUserId,
        ResModel[list[UserCatalogInfo]],
        fetch_prdcer_ctlgs,
        wrap_output=True,
    )
    return response


@app.post(CONF.fetch_ctlg_lyrs, response_model=ResModel[list[ResLyrMapData]])
async def fetch_catalog_layers(req: ReqModel[ReqFetchCtlgLyrs]):
    response = await request_handling(
        req.request_body,
        ReqFetchCtlgLyrs,
        ResModel[list[ResLyrMapData]],
        fetch_ctlg_lyrs,
        wrap_output=True,
    )
    return response


# Authentication
@app.post(CONF.login, response_model=ResModel[dict[str, Any]], tags=["Authentication"])
async def login(req: ReqModel[ReqUserLogin]):
    response = await request_handling(
            req.request_body,
            ReqUserLogin,
            ResModel[dict[str, Any]],
            login_user,
            wrap_output=True,
        )
    return response


@app.post(
    CONF.refresh_token, response_model=ResModel[dict[str, Any]], tags=["Authentication"]
)
async def refresh_token(req: ReqModel[ReqRefreshToken]):
    try:
        if CONF.firebase_api_key != "":
            response = await request_handling(
                req.request_body,
                ReqRefreshToken,
                ResModel[dict[str, Any]],
                refresh_id_token,
                wrap_output=True,
            )
        else:
            response = {
                "message": "Request received",
                "request_id": "req-228dc80c-e545-4cfb-ad07-b140ee7a8aac",
                "data": {
                    "kind": "identitytoolkit#VerifyPasswordResponse",
                    "localId": "dkD2RHu4pcUTMXwF2fotf6rFfK33",
                    "email": "testemail@gmail.com",
                    "displayName": "string",
                    "idToken": "eyJhbGciOiJSUzI1NiIsImtpZCI6ImNlMzcxNzMwZWY4NmViYTI5YTUyMTJkOWI5NmYzNjc1NTA0ZjYyYmMiLCJ0eXAiOiJKV1QifQ.eyJuYW1lIjoic3RyaW5nIiwiaXNzIjoiaHR0cHM6Ly9zZWN1cmV0b2tlbi5nb29nbGUuY29tL2Zpci1sb2NhdG9yLTM1ODM5IiwiYXVkIjoiZmlyLWxvY2F0b3ItMzU4MzkiLCJhdXRoX3RpbWUiOjE3MjM0MjAyMzQsInVzZXJfaWQiOiJka0QyUkh1NHBjVVRNWHdGMmZvdGY2ckZmSzMzIiwic3ViIjoiZGtEMlJIdTRwY1VUTVh3RjJmb3RmNnJGZkszMyIsImlhdCI6MTcyMzQyMDIzNCwiZXhwIjoxNzIzNDIzODM0LCJlbWFpbCI6InRlc3RlbWFpbEBnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6ZmFsc2UsImZpcmViYXNlIjp7ImlkZW50aXRpZXMiOnsiZW1haWwiOlsidGVzdGVtYWlsQGdtYWlsLmNvbSJdfSwic2lnbl9pbl9wcm92aWRlciI6InBhc3N3b3JkIn19.BrHdEDcjycdMj1hdbAtPI4r1HmXPW7cF9YwwNV_W2nH-BcYTXcmv7nK964bvXUCPOw4gSqsk7Nsgig0ATvhLr6bwOuadLjBwpXAbPc2OZNw-m6_ruINKoAyP1FGs7FvtOWNC86-ckwkIKBMB1k3-b2XRvgDeD2WhZ3bZbEAhHohjHzDatWvSIIwclHMQIPRN04b4-qXVTjtDV0zcX6pgkxTJ2XMRTgrpwoAxCNoThmRWbJjILmX-amzmdAiCjFzQW1lCP_RIR4ZOT0blLTupDxNFmdV5mj6oV7WZmH-NPO4sGmfHDoKVwoFX8s82E77p-esKUF7QkRDSCtaSQES3og",
                    "registered": True,
                    "refreshToken": "AMf-vByZFCBWektg34QkcoletyWBbPbLRccBgL32KjX04dwzTtIePkIQ5B48T9oRP9wFBF876Ts-FjBa2ZKAUSm00bxIzigAoX7yEancXdGaLXXQuqTyZ2tdCWtcac_XSd-_EpzuOiZ_6Zoy7d-Y0i14YQNRW3BdEfgkwU6tHRDZTfg0K-uQi3iorbO-9l_O4_REq-sWRTssxyXIik4vKdtrphyhhwuOUTppdRSeiZbaUGZOcJSi7Es",
                    "expiresIn": "3600",
                    "created_at": "2024-08-11T19:50:33.617798",
                },
            }
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail="Token refresh failed")


@app.post(
    CONF.reset_password,
    response_model=ResModel[dict[str, Any]],
    tags=["Authentication"],
)
async def reset_password_endpoint(req: ReqModel[ReqResetPassword]):
    response = await request_handling(
        req.request_body,
        ReqResetPassword,
        ResModel[dict[str, Any]],
        reset_password,
        wrap_output=True,
    )
    return response


@app.post(
    CONF.confirm_reset, response_model=ResModel[dict[str, Any]], tags=["Authentication"]
)
async def confirm_reset_endpoint(req: ReqModel[ReqConfirmReset]):
    response = await request_handling(
        req.request_body,
        ReqConfirmReset,
        ResModel[dict[str, Any]],
        confirm_reset,
        wrap_output=True,
    )
    return response


@app.post(
    CONF.change_password,
    response_model=ResModel[dict[str, Any]],
    dependencies=[Depends(JWTBearer())],
    tags=["Authentication"],
)
async def change_password_endpoint(req: ReqModel[ReqChangePassword], request: Request):
    response = await request_handling(
        req.request_body,
        ReqChangePassword,
        ResModel[dict[str, Any]],
        change_password,
        wrap_output=True,
    )
    return response


@app.post(
    CONF.change_email,
    response_model=ResModel[dict[str, Any]],
    dependencies=[Depends(JWTBearer())],
    tags=["Authentication"],
)
async def change_email_endpoint(req: ReqModel[ReqChangeEmail], request: Request):
    response = await request_handling(
        req.request_body,
        ReqChangeEmail,
        ResModel[dict[str, Any]],
        change_email,
        wrap_output=True,
    )
    return response


@app.post(
    CONF.user_profile,
    response_model=ResModel[dict[str, Any]],
    dependencies=[Depends(JWTBearer())],
)
async def get_user_profile_endpoint(req: ReqModel[ReqUserProfile], request: Request):
    response = await request_handling(
        req.request_body,
        ReqUserProfile,
        ResModel[dict[str, Any]],
        get_user_profile,
        wrap_output=True,
    )
    return response


@app.post(CONF.cost_calculator, response_model=ResModel[ResCostEstimate])
async def cost_calculator_endpoint(req: ReqModel[ReqFetchDataset], request: Request):
    response = await request_handling(
        req.request_body,
        ReqFetchDataset,
        ResModel[ResCostEstimate],
        calculate_cost,
        wrap_output=True,
    )
    return response


@app.post(
    CONF.save_draft_catalog,
    response_model=ResModel[str],
    dependencies=[Depends(JWTBearer())],
)
async def save_draft_catalog_endpoint(
    req: ReqModel[ReqSavePrdcerCtlg], request: Request
):
    response = await request_handling(
        req.request_body,
        ReqSavePrdcerCtlg,
        ResModel[str],
        save_draft_catalog,
        wrap_output=True,
    )
    return response


@app.get(CONF.fetch_gradient_colors, response_model=ResModel[list[list[str]]])
async def ep_fetch_gradient_colors():
    response = await request_handling(
        None, None, ResModel[list[list[str]]], fetch_gradient_colors, wrap_output=True
    )
    return response


@app.post(
    CONF.gradient_color_based_on_zone,
    response_model=ResModel[list[ResGradientColorBasedOnZone]],
)
async def ep_process_color_based_on(
    req: ReqModel[ReqGradientColorBasedOnZone], request: Request
):
    response = await request_handling(
        req.request_body,
        ReqGradientColorBasedOnZone,
        ResModel[list[ResGradientColorBasedOnZone]],
        process_color_based_on,
        wrap_output=True,
    )
    return response


@app.post(
    CONF.check_street_view,
    response_model=ResModel[dict[str, bool]],
    dependencies=[Depends(JWTBearer())],
)
async def check_street_view(req: ReqModel[ReqStreeViewCheck]):
    response = await request_handling(
        req.request_body,
        ReqStreeViewCheck,
        ResModel[dict[str, Any]],
        check_street_view_availability,
        wrap_output=True,
    )
    return response


@app.put(
    CONF.update_stripe_customer,
    response_model=ResModel[dict],
    description="Update an existing customer in stripe",
    tags=["stripe customers"],
)
async def update_stripe_customer_endpoint(req: ReqModel[CustomerReq]):
    response = await request_handling(
        req.request_body, CustomerReq, ResModel[dict], update_customer, wrap_output=True
    )
    return response


@app.get(
    CONF.list_stripe_customers,
    response_model=ResModel[list[dict]],
    description="list all customers in stripe",
    tags=["stripe customers"],
)
async def list_stripe_customers_endpoint():
    response = await request_handling(
        None, None, ResModel[list[dict]], list_customers, wrap_output=True
    )
    return response


@app.post(
    CONF.fetch_stripe_customer,
    response_model=ResModel[dict],
    description="Fetch a customer in stripe",
    tags=["stripe customers"],
)
async def fetch_stripe_customer_endpoint(req: ReqModel[ReqUserId]):
    response = await request_handling(
        req.request_body, ReqUserId, ResModel[dict], fetch_customer, wrap_output=True
    )
    return response


# Stripe Wallet
@app.post(
    CONF.top_up_wallet,
    description="top_up a customer's wallet in stripe",
    tags=["stripe wallet"],
    response_model=ResModel[dict],
)
async def top_up_wallet_endpoint(req: ReqModel[TopUpWalletReq]):
    response = await request_handling(
        req.request_body, TopUpWalletReq, ResModel[dict], top_up_wallet, wrap_output=True
    )
    return response


@app.get(
    CONF.fetch_wallet,
    description="Fetch a customer's wallet in stripe",
    tags=["stripe wallet"],
    response_model=ResModel[dict],
)
async def fetch_wallet_endpoint(user_id: str):
    resp = await fetch_wallet(user_id)
    response = ResModel(
        data=resp,
        message="Wallet fetched successfully",
        request_id=str(uuid.uuid4()),
    )
    return response

@app.post(
    CONF.deduct_wallet,
    description="Deduct amount from customer's wallet in stripe",
    tags=["stripe wallet"],
    response_model=ResModel[dict],
)
async def deduct_from_wallet_endpoint(req: ReqModel[DeductWalletReq]):
    response = await request_handling(
        req.request_body, DeductWalletReq, ResModel[dict], deduct_from_wallet, wrap_output=True
    )
    return response

# Stripe Subscriptions
@app.post(
    CONF.create_stripe_subscription,
    description="Create a new subscription in stripe",
    tags=["stripe subscriptions"],
    response_model=ResModel[dict],
)
async def create_stripe_subscription_endpoint(req: ReqModel[SubscriptionCreateReq]):
    subscription = await create_subscription(req.request_body)
    response = ResModel(
        data=subscription,
        message="Subscription created successfully",
        request_id=str(uuid.uuid4()),
    )
    return response


@app.put(
    CONF.update_stripe_subscription,
    response_model=ResModel[dict],
    description="Update an existing subscription in stripe",
    tags=["stripe subscriptions"],
)
async def update_stripe_subscription_endpoint(
    subscription_id: str, req: ReqModel[SubscriptionUpdateReq]
):
    subscription = await update_subscription(subscription_id, req.request_body.seats)
    response = ResModel(
        data=subscription,
        message="Subscription updated successfully",
        request_id=str(uuid.uuid4()),
    )
    return response


@app.delete(
    CONF.deactivate_stripe_subscription,
    response_model=ResModel[dict],
    description="Deactivate an existing subscription in stripe",
    tags=["stripe subscriptions"],
)
async def deactivate_stripe_subscription_endpoint(subscription_id: str):
    deactivated = await deactivate_subscription(subscription_id)
    response = ResModel(
        data=deactivated,
        message="Subscription deactivated successfully",
        request_id=str(uuid.uuid4()),
    )
    return response


@app.put(
    CONF.update_stripe_payment_method,
    response_model=ResModel[dict],
    description="Update an existing payment method in stripe",
    tags=["stripe payment methods"],
)
async def update_stripe_payment_method_endpoint(
    payment_method_id: str, req: ReqModel[PaymentMethodUpdateReq]
):
    payment_method = await update_payment_method(payment_method_id, req.request_body)
    response = ResModel(
        data=payment_method,
        message="Payment method updated successfully",
        request_id=str(uuid.uuid4()),
    )
    return response


@app.post(
    CONF.attach_stripe_payment_method,
    response_model=ResModel[dict],
    description="Add an existing stripe payment method to a customer",
    tags=["stripe payment methods"],
)
async def attach_stripe_payment_method_endpoint(req: ReqModel[PaymentMethodAttachReq]):
    data = await attach_payment_method(
        req.request_body.user_id, req.request_body.payment_method_id
    )
    response = ResModel(
        data=data,
        message="Payment method attached successfully",
        request_id=str(uuid.uuid4()),
    )
    return response


@app.delete(
    CONF.detach_stripe_payment_method,
    response_model=ResModel[dict],
    description="Delete an existing payment method in stripe",
    tags=["stripe payment methods"],
)
async def delete_stripe_payment_method_endpoint(payment_method_id: str):
    data = await delete_payment_method(payment_method_id)
    response = ResModel(
        data=data,
        message="Payment method deleted successfully",
        request_id=str(uuid.uuid4()),
    )
    return response


@app.get(
    CONF.list_stripe_payment_methods,
    response_model=ResModel[list[dict]],
    description="list all payment methods in stripe",
    tags=["stripe payment methods"],
)
async def list_stripe_payment_methods_endpoint(user_id: str):
    payment_methods = await list_payment_methods(user_id)
    response = ResModel(
        data=payment_methods,
        message="Payment methods retrieved successfully",
        request_id=str(uuid.uuid4()),
    )
    return response


@app.put(
    CONF.set_default_stripe_payment_method,
    response_model=ResModel[dict],
    description="Set a default payment method in stripe",
    tags=["stripe payment methods"],
)
async def set_default_payment_method_endpoint(user_id: str, payment_method_id: str):
    default_payment_method = await set_default_payment_method(
        user_id, payment_method_id
    )
    response = ResModel(
        data=default_payment_method,
        message="Default payment method set successfully",
        request_id=str(uuid.uuid4()),
    )
    return response


@app.post(
    CONF.create_stripe_product,
    response_model=ResModel[dict],
    description="Create a new subscription product in stripe",
    tags=["stripe products"],
)
async def create_stripe_product_endpoint(req: ReqModel[ProductReq]):
    product = await create_stripe_product(req.request_body)

    response = ResModel(
        data=product,
        message="Product created successfully",
        request_id=str(uuid.uuid4()),
    )
    return response


@app.put(
    CONF.update_stripe_product,
    response_model=ResModel[dict],
    description="Update an existing subscription product in stripe",
    tags=["stripe products"],
)
async def update_stripe_product_endpoint(product_id: str, req: ReqModel[ProductReq]):
    product = await update_stripe_product(product_id, req.request_body)
    response = ResModel(
        data=product,
        message="Product updated successfully",
        request_id=str(uuid.uuid4()),
    )

    return response.model_dump()


@app.delete(
    CONF.delete_stripe_product,
    response_model=ResModel[dict],
    description="Delete an existing subscription product in stripe",
    tags=["stripe products"],
)
async def delete_stripe_product_endpoint(product_id: str):
    deleted = await delete_stripe_product(product_id)
    response = ResModel(
        data=deleted,
        message="Product deleted successfully",
        request_id=str(uuid.uuid4()),
    )
    return response


@app.get(
    CONF.list_stripe_products,
    description="list all subscription products in stripe",
    tags=["stripe products"],
    response_model=ResModel[list[dict]],
)
async def list_stripe_products_endpoint():
    products = await list_stripe_products()
    response = ResModel(
        data=products,
        message="Products retrieved successfully",
        request_id=str(uuid.uuid4()),
    )
    return response


@app.post("/fastapi/create_user_profile", response_model=list[dict[Any, Any]])
async def create_user_profile_endpoint(req: ReqModel[ReqCreateUserProfile]):

    response_1 = await request_handling(
        req.request_body,
        ReqCreateFirebaseUser,
        dict[Any, Any],
        create_firebase_user,
        wrap_output=True,
    )

    response_2 = await request_handling(
        response_1["data"]["user_id"],
        None,
        dict[Any, Any],
        create_stripe_customer,
        wrap_output=True,
    )

    req_user_profile = ReqCreateUserProfile(
        user_id=response_1["data"]["user_id"],
        username=req.request_body.username,
        password=req.request_body.password,
        email=req.request_body.email,
    )

    response_3 = await request_handling(
        req_user_profile,
        None,
        dict[Any, Any],
        create_user_profile,
        wrap_output=True,
    )
    response = [response_1, response_2, response_3]
    return response


@app.post(
    "/fastapi/update_user_profile",
    response_model=ResModel[dict[str, Any]],
    dependencies=[Depends(JWTBearer())]
)
async def update_user_profile_endpoint(req: ReqModel[UserProfileSettings]):
    response = await request_handling(
        req.request_body,
        UserProfileSettings,
        ResModel[dict[str, Any]],
        update_profile,
        wrap_output=True,
    )
    return response

@app.post(
        CONF.gradient_color_based_on_zone+"_llm",
        response_model=ResModel[ValidationResult],   
)
async def ep_process_color_based_on_agent(
    req:ReqModel[ReqPrompt], request: Request):
    response = await request_handling(
        req.request_body,
        ReqPrompt,
        ResModel[ValidationResult],
        process_color_based_on_agent,
        wrap_output=True,
    )
    return response

# from LLM import BusinessPromptRequest, BusinessPromptResponse, analyze_prompt_completeness,create_vector_store

# vector_store = create_vector_store()


# @app.post("/analyze-business-prompt")
# async def analyze_business_prompt(request: BusinessPromptRequest):

#     response = await analyze_prompt_completeness(request.user_prompt, vector_store=vector_store)
#     return response

@app.post(
    CONF.filter_based_on,
    response_model=ResModel[list[ResGradientColorBasedOnZone]],
)
async def filter_based_on_(
    req: ReqModel[ReqFilter], request: Request
):
    response = await request_handling(
        req.request_body,
        ReqFilter,
        ResModel[list[ResGradientColorBasedOnZone]],
        filter_based_on,
        wrap_output=True,
    )
    return response

@app.post(CONF.distance_drive_time_polygon, response_model=ResModel[Res_src_distination])
async def distance_drivetime_polygon(req:ReqModel[Req_src_distination]):
    response = await request_handling(
        req.request_body,
        Req_src_distination,
        ResModel[Res_src_distination],
        load_distance_drive_time_polygon,
        wrap_output = True
    )
    return response

