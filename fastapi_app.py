import logging
import uuid
from typing import Optional, Type, Callable, Awaitable, Any, TypeVar
from database import Database
from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException, status
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from firebase_admin.auth import InvalidIdTokenError
from pydantic import BaseModel
from pydantic import ValidationError

from all_types.myapi_dtypes import ReqApplyZoneLayers, ResApplyZoneLayers
from all_types.myapi_dtypes import (
    ReqUserId,
    ResUserLayers,
    ReqSavePrdcerCtlg,
    ResSavePrdcerCtlg,
)
from all_types.myapi_dtypes import (
    ResAllCards,
    ResAcknowlg,
    ResTypeMapData,
    ResCountryCityData,
    ResNearbyCategories,
    ReqCreateLyr,
    ResCreateLyr,
    ReqSavePrdcerLyer,
    ReqPrdcerLyrMapData,
    ResPrdcerLyrMapData,
    ReqCreateUserProfile,
    ResCreateUserProfile,
    ReqModel,
    ReqUserLogin,
    ReqUserProfile,
    ResUserProfile,
    ResUserLogin,
    ReqConfirmReset,
    ResConfirmReset,
    ReqResetPassword,
    ResResetPassword,
    ResChangePassword,
    ReqChangePassword,
)
from all_types.myapi_dtypes import ResUserCatalogs, ReqFetchCtlgLyrs, ResCtlgLyrs
from auth import (
    create_user_profile,
    get_user_account,
    login_user,
    my_verify_id_token,
    reset_password,
    confirm_reset,
    change_password,
)
from config_factory import get_conf
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
    apply_zone_layers,
)
from data_fetcher import fetch_nearby_categories
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
            if full_request:
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


@app.get(CONF.fetch_acknowlg_id, response_model=ResAcknowlg)
async def fetch_acknowlg_id():
    response = await http_handling(
        None,
        None,
        ResAcknowlg,
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


@app.post(CONF.create_layer, response_model=ResCreateLyr)
async def create_layer(req: ReqModel[ReqCreateLyr], request:Request):
    if req.request_body.action =='sample':
        request=None
    response = await http_handling(
        req,
        ReqCreateLyr,
        ResCreateLyr,
        fetch_country_city_category_map_data,
        request
    )
    return response


@app.post(CONF.save_producer_layer, response_model=ResAcknowlg)
async def save_producer_layer(req: ReqModel[ReqSavePrdcerLyer], request:Request):
    response = await http_handling(
        req,
        ReqSavePrdcerLyer,
        ResAcknowlg,
        save_lyr,
        request
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
        req,
        ReqSavePrdcerCtlg,
        ResSavePrdcerCtlg,
        create_save_prdcer_ctlg,
        request
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


@app.post(CONF.apply_zone_layers, response_model=ResApplyZoneLayers)
async def apply_zone_layers_endpoint(req: ReqModel[ReqApplyZoneLayers]):
    response = await http_handling(
        req, ReqApplyZoneLayers, ResApplyZoneLayers, apply_zone_layers
    )
    return response


@app.post(CONF.create_user_profile, response_model=ResCreateUserProfile)
async def create_user_profile_endpoint(req: ReqModel[ReqCreateUserProfile]):
    response = await http_handling(
        req, ReqCreateUserProfile, ResCreateUserProfile, create_user_profile
    )
    return response


@app.post(CONF.login, response_model=ResUserLogin)
async def login(req: ReqModel[ReqUserLogin]):
    response = await http_handling(req, ReqUserLogin, ResUserLogin, login_user)
    return response


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


@app.post(CONF.change_password, response_model=ResChangePassword)
async def change_password_endpoint(req: ReqModel[ReqChangePassword], request: Request):
    response = await http_handling(
        req, ReqChangePassword, ResChangePassword, change_password
    )
    return response


# @app.post("/refresh-token")
# async def refresh_token(token: dict = Depends(verify_token)):
#     try:
#         # Create a new custom token
#         new_token = auth.create_custom_token(token['uid'])
#         return {"access_token": new_token, "token_type": "bearer"}
#     except Exception as e:
#         raise HTTPException(status_code=400, detail="Token refresh failed")
