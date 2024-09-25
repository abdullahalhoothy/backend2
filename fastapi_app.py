import logging
import uuid
from typing import Optional, Type, Callable, Awaitable, Any, TypeVar, List, Dict

from fastapi import HTTPException, status, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from pydantic import ValidationError
from collections import Counter

from all_types.myapi_dtypes import (
    ReqFetchDataset,
    ReqSavePrdcerLyer,
    ReqPrdcerLyrMapData,
    ReqCreateUserProfile,
    ReqModel,
    ReqUserLogin,
    ReqUserProfile,
    ReqConfirmReset,
    ReqResetPassword,
    ReqChangePassword,
    ReqCostEstimate,
    ReqUserId,
    ReqSavePrdcerCtlg,
    ReqGradientColorBasedOnZone,
    ReqRefreshToken,
    ReqChangeEmail,
    ReqAddPaymentMethod,
    ReqGetPaymentMethods,
    ReqLocation
)
from all_types.myapi_dtypes import ReqFetchCtlgLyrs
from all_types.response_dtypes import (
    ResModel,
    ResAllCards,
    ResUserLayers,
    ResCtlgLyrs,
    # ResApplyZoneLayers,
    ResCreateUserProfile,
    ResSavePrdcerCtlg,
    ResTypeMapData,
    ResCountryCityData,
    ResNearbyCategories,
    ResPrdcerLyrMapData,
    ResFetchDataset,
    ResUserCatalogs,
    ResUserLogin,
    ResUserProfile,
    ResResetPassword,
    ResConfirmReset,
    ResCostEstimate,
    ResAddPaymentMethod,
    ResfetchGradientColors,
    ResGradientColorBasedOnZone,
    ResUserRefreshToken,
    ResGetPaymentMethods
)
from auth import (
    create_user_profile,
    get_user_account,
    login_user,
    my_verify_id_token,
    reset_password,
    confirm_reset,
    change_password,
    refresh_id_token,
    change_email
)
from payment_handler import add_payment_method, get_payment_methods
from config_factory import get_conf
from cost_calculator import calculate_cost
from data_fetcher import (
    fetch_country_city_data,
    fetch_catlog_collection,
    fetch_layer_collection,
    fetch_country_city_category_map_data,
    save_lyr,
    fetch_user_lyrs,
    fetch_lyr_map_data,
    create_save_prdcer_ctlg,
    fetch_prdcer_ctlgs,
    fetch_ctlg_lyrs,
    # apply_zone_layers,
    fetch_nearby_categories,
    save_draft_catalog,
    fetch_gradient_colors,
    gradient_color_based_on_zone,
    cover_circle_with_seven_circles,
    print_circle_hierarchy
)

from google_api_connector import (
    fetch_from_google_maps_api
)
from database import Database
from logging_wrapper import log_and_validate

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)
U = TypeVar("U", bound=BaseModel)

CONF = get_conf()

app = FastAPI()

# Enable CORS
origins = [CONF.enable_CORS_url]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    await Database.create_pool()


@app.on_event("shutdown")
async def shutdown_event():
    await Database.close_pool()


@log_and_validate(logger)
async def http_handling(
    req: Optional[T],
    input_type: Optional[Type[T]],
    output_type: Type[U],
    custom_function: Optional[Callable[..., Awaitable[Any]]],
    full_request: Request = None,
):
    try:
        output = ""
        if req is not None:
            # Get all headers
            authorization = None
            if full_request and CONF.firebase_api_key != "":
                headers = full_request.headers
                # Check for access token in the Authorization header
                authorization = headers.get("Authorization", None)
                if authorization:
                    try:
                        # Extract the token from the "Bearer" scheme
                        scheme, access_token = authorization.split()
                        if scheme.lower() != "bearer":
                            raise HTTPException(
                                status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid authentication scheme",
                                headers={"WWW-Authenticate": "Bearer"},
                            )

                        decoded_token = await my_verify_id_token(access_token)
                        token_user_id = decoded_token["uid"]
                        # Check if the token user_id matches the requested user_id
                        if (
                            hasattr(req.request_body, "user_id")
                            and token_user_id != req.request_body.user_id
                        ):
                            raise HTTPException(
                                status_code=status.HTTP_403_FORBIDDEN,
                                detail="You can only access your own profile",
                            )
                    except Exception as e:
                        logger.error(f"Token validation error: {str(e)}")
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid request body: {str(e)}",
                        ) from e
                else:
                    # If no authorization header is present, you might want to handle this case
                    # depending on your security requirements. For example:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authorization header missing",
                        headers={"WWW-Authenticate": "Bearer"},
                    )

            req = req.request_body
            try:
                input_type.model_validate(req)
            except ValidationError as e:
                logger.error("Request validation error: %s", str(e))
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid request body: {str(e)}",
                ) from e

        if custom_function is not None:
            try:
                output = await custom_function(req=req)
            except HTTPException:
                # If it's already an HTTPException, just re-raise it
                raise
            except Exception as e:
                # For any other type of exception, wrap it in an HTTPException
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"An unexpected error occurred: {str(e)}",
                ) from e

        request_id = "req-" + str(uuid.uuid4())

        try:
            res_body = output_type(
                message="Request received",
                request_id=request_id,
                data=output,
            )
        except ValidationError as e:
            logger.error(f"Response validation error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while constructing the response",
            ) from e

        return res_body

    except HTTPException as http_exc:
        # Log the exception and return it directly
        logger.error(f"HTTP exception: {http_exc.detail}")
        return JSONResponse(
            status_code=http_exc.status_code, content={"detail": http_exc.detail}
        )
    except Exception as e:
        # Catch any other unexpected exceptions
        logger.critical(f"Unexpected error in http_handling: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred"},
        )


# deprecated=True
@app.post(CONF.http_catlog_data, response_model=ResTypeMapData, deprecated=True)
async def catlog_data(catlog_req: ReqModel[ReqFetchCtlgLyrs]):
    # Step 3: Redirect traffic to the new endpoint
    new_url = app.url_path_for(CONF.fetch_ctlg_lyrs)
    return RedirectResponse(url=new_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get(CONF.fetch_acknowlg_id, response_model=ResModel[str])
async def fetch_acknowlg_id():
    response = await http_handling(
        None,
        None,
        ResModel[str],
        None,
    )
    return response


@app.get(CONF.catlog_collection, response_model=ResAllCards)
async def catlog_collection():
    response = await http_handling(
        None,
        None,
        ResAllCards,
        fetch_catlog_collection,
    )
    return response


@app.get(CONF.layer_collection, response_model=ResAllCards)
async def layer_collection():
    response = await http_handling(
        None,
        None,
        ResAllCards,
        fetch_layer_collection,
    )
    return response


@app.get(CONF.country_city, response_model=ResCountryCityData)
async def country_city():
    response = await http_handling(
        None,
        None,
        ResCountryCityData,
        fetch_country_city_data,
    )
    return response


@app.get(CONF.nearby_categories, response_model=ResNearbyCategories)
async def nearby_categories():
    response = await http_handling(
        None,
        None,
        ResNearbyCategories,
        fetch_nearby_categories,
    )
    return response


@app.post(CONF.fetch_dataset, response_model=ResModel[ResFetchDataset])
async def fetch_dataset_ep(req: ReqModel[ReqFetchDataset], request: Request):
    if req.request_body.action == "sample":
        request = None
    response = await http_handling(
        req,
        ReqFetchDataset,
        ResModel[ResFetchDataset],
        fetch_country_city_category_map_data,
        request,
    )
    return response


@app.post(CONF.save_layer, response_model=ResModel[str])
async def save_layer_ep(req: ReqModel[ReqSavePrdcerLyer], request: Request):
    response = await http_handling(
        req, ReqSavePrdcerLyer, ResModel[str], save_lyr, request
    )
    return response


@app.post(CONF.user_layers, response_model=ResUserLayers)
async def user_layers(req: ReqModel[ReqUserId]):
    response = await http_handling(req, ReqUserId, ResUserLayers, fetch_user_lyrs)
    return response


@app.post(CONF.prdcer_lyr_map_data, response_model=ResPrdcerLyrMapData)
async def prdcer_lyr_map_data(req: ReqModel[ReqPrdcerLyrMapData]):
    response = await http_handling(
        req, ReqPrdcerLyrMapData, ResPrdcerLyrMapData, fetch_lyr_map_data
    )
    return response


@app.post(CONF.save_producer_catalog, response_model=ResSavePrdcerCtlg)
async def save_producer_catalog(req: ReqModel[ReqSavePrdcerCtlg], request: Request):
    response = await http_handling(
        req, ReqSavePrdcerCtlg, ResSavePrdcerCtlg, create_save_prdcer_ctlg, request
    )
    return response


@app.post(CONF.user_catalogs, response_model=ResUserCatalogs)
async def user_catalogs(req: ReqModel[ReqUserId]):
    response = await http_handling(req, ReqUserId, ResUserCatalogs, fetch_prdcer_ctlgs)
    return response


@app.post(CONF.fetch_ctlg_lyrs, response_model=ResCtlgLyrs)
async def fetch_catalog_layers(req: ReqModel[ReqFetchCtlgLyrs]):
    response = await http_handling(req, ReqFetchCtlgLyrs, ResCtlgLyrs, fetch_ctlg_lyrs)
    return response


# @app.post(CONF.apply_zone_layers, response_model=ResApplyZoneLayers)
# async def apply_zone_layers_endpoint(req: ReqModel[ReqApplyZoneLayers]):
#     response = await http_handling(
#         req, ReqApplyZoneLayers, ResApplyZoneLayers, apply_zone_layers
#     )
#     return response


@app.post(CONF.create_user_profile, response_model=ResCreateUserProfile)
async def create_user_profile_endpoint(req: ReqModel[ReqCreateUserProfile]):
    response = await http_handling(
        req, ReqCreateUserProfile, ResCreateUserProfile, create_user_profile
    )
    return response


@app.post(CONF.login, response_model=ResUserLogin)
async def login(req: ReqModel[ReqUserLogin]):
    if CONF.firebase_api_key != "":
        response = await http_handling(req, ReqUserLogin, ResUserLogin, login_user)
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

##################################################################################################################### 
@app.post(CONF.refresh_token,response_model=ResUserRefreshToken)
async def refresh_token(req:ReqModel[ReqRefreshToken]):
    try:
        if CONF.firebase_api_key != "":
            response = await http_handling(req,ReqRefreshToken,ResUserRefreshToken,refresh_id_token)
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
#########################################################################################################################


@app.post(CONF.user_profile, response_model=ResUserProfile)
async def get_user_profile_endpoint(req: ReqModel[ReqUserProfile], request: Request):
    response = await http_handling(
        req, ReqUserProfile, ResUserProfile, get_user_account, request
    )
    return response


@app.post(CONF.reset_password, response_model=ResResetPassword)
async def reset_password_endpoint(req: ReqModel[ReqResetPassword]):
    response = await http_handling(
        req, ReqResetPassword, ResResetPassword, reset_password
    )
    return response


@app.post(CONF.confirm_reset, response_model=ResConfirmReset)
async def confirm_reset_endpoint(req: ReqModel[ReqConfirmReset]):
    response = await http_handling(req, ReqConfirmReset, ResConfirmReset, confirm_reset)
    return response


@app.post(CONF.change_password, response_model=ResModel[Dict[str, Any]])
async def change_password_endpoint(req: ReqModel[ReqChangePassword], request: Request):
    response = await http_handling(
        req, ReqChangePassword, ResModel[Dict[str, Any]], change_password, request
    )
    return response


@app.post(CONF.change_email, response_model=ResModel[Dict[str, Any]])
async def change_email_endpoint(req: ReqModel[ReqChangeEmail], request: Request):
    response = await http_handling(
        req, ReqChangeEmail, ResModel[Dict[str, Any]], change_email, request
    )
    return response

@app.post(CONF.cost_calculator, response_model=ResModel[ResCostEstimate])
async def cost_calculator_endpoint(req: ReqModel[ReqCostEstimate], request: Request):
    response = await http_handling(
        req, ReqCostEstimate, ResModel[ResCostEstimate], calculate_cost
    )
    return response


@app.post(CONF.save_draft_catalog, response_model=ResSavePrdcerCtlg)
async def save_draft_catalog_endpoint(
    req: ReqModel[ReqSavePrdcerCtlg], request: Request
):
    response = await http_handling(
        req, ReqSavePrdcerCtlg, ResSavePrdcerCtlg, save_draft_catalog, request
    )
    return response

@app.get(CONF.fetch_gradient_colors, response_model=ResfetchGradientColors)
async def fetch_gradient_colors_endpoint():
    response = await http_handling(
        None,None,ResfetchGradientColors, fetch_gradient_colors)
    return response


@app.post(CONF.gradient_color_based_on_zone, response_model=ResModel[List[ResGradientColorBasedOnZone]])
async def gradient_color_based_on_zone_endpoint(
    req: ReqModel[ReqGradientColorBasedOnZone],
    request: Request):
    response = await http_handling(
        req,
        ReqGradientColorBasedOnZone,
        ResModel[List[ResGradientColorBasedOnZone]],
        gradient_color_based_on_zone)
    return response


@app.post(CONF.add_payment_method, response_model=ResModel[ResAddPaymentMethod])
async def add_payment_method_endpoint(req: ReqAddPaymentMethod, request: Request):
    response = await http_handling(
        req,
        ReqAddPaymentMethod,
        ResModel[ResAddPaymentMethod],
        add_payment_method,
        request
    )
    return response

@app.post(CONF.get_payment_methods, response_model=ResModel[ResGetPaymentMethods])
async def get_payment_methods_endpoint(req: ReqGetPaymentMethods, request: Request):
    response = await http_handling(
        req,
        ReqGetPaymentMethods,
        ResModel[ResGetPaymentMethods],
        get_payment_methods,
        request
    )
    return response



############################################# Test
@app.post(CONF.fetch_query_from_map)
async def get_search_query_results(req:ReqLocation):
    req.radius *= 1000
    main_circle = cover_circle_with_seven_circles((req.lat,req.lng),req.radius,is_center_circle=True)
    all_circles = print_circle_hierarchy(main_circle)
    ## circle_number:lat:lng:radius
    id_set = set()
    result = []
    for circle in all_circles:
        fields = circle.split(':')
        circle_number,req.lat,req.lng,req.radius = fields[0],fields[1],fields[2],fields[3]
        places = await fetch_from_google_maps_api(req)
        for place in places:
            if place['id'] not in id_set:
                id_set.add(place['id'])
                result.append((place,float(circle_number)*float(place['rating'])))
    result.sort(key=lambda p: p[1],reverse=True)
    return result
#############################################