from fastapi import Body, HTTPException, status, FastAPI, Request, Depends
from backend_common.auth import JWTBearer
from backend_common.dtypes.auth_dtypes import (
    ReqCreateFirebaseUser,
    ReqChangeEmail,
    ReqResetPassword,
    ReqConfirmReset,
    ReqChangePassword,
    ReqRefreshToken,
    UserId,
    ReqUserLogin,
    ReqUserProfile,
    ReqUserProfile,
)
from backend_common.request_processor import request_handling
from typing import Dict, List, TypeVar, Generic, Literal, Any, Optional, Union
from backend_common.auth import (
    create_firebase_user,
    login_user,
    my_verify_id_token,
    reset_password,
    confirm_reset,
    change_password,
    refresh_id_token,
    change_email,
)
from backend_common.stripe_backend.customers import create_stripe_customer

app = FastAPI()


@app.get("/index", dependencies=[Depends(JWTBearer())])
# this needs to use request_handling
def index():
    return {"message": "Hello World"}


# @app.post("/create_firebase_stripe_user", response_model=list[Dict[Any, Any]])
# async def create_user_profile_endpoint(req: ReqCreateFirebaseUser):

#     response_1 = await request_handling(
#         req, ReqCreateFirebaseUser, dict[Any, Any], create_firebase_user
#     )
#     response_2 = await request_handling(
#         response_1["user_id"], None, dict[Any, Any], create_stripe_customer
#     )
#     response = [response_1, response_2]
#     return response


# @app.post("/login", response_model=dict[Any, Any])
# async def login(req: ReqUserLogin):
#     # if CONF.firebase_api_key != "":
#     response = await request_handling(
#         req, ReqUserLogin, dict[Any, Any], login_user
#     )
#     # else:
#     #     response = {
#     #         "message": "Request received",
#     #         "request_id": "req-228dc80c-e545-4cfb-ad07-b140ee7a8aac",
#     #         "data": {
#     #             "kind": "identitytoolkit#VerifyPasswordResponse",
#     #             "localId": "dkD2RHu4pcUTMXwF2fotf6rFfK33",
#     #             "email": "testemail@gmail.com",
#     #             "displayName": "string",
#     #             "idToken": "eyJhbGciOiJSUzI1NiIsImtpZCI6ImNlMzcxNzMwZWY4NmViYTI5YTUyMTJkOWI5NmYzNjc1NTA0ZjYyYmMiLCJ0eXAiOiJKV1QifQ.eyJuYW1lIjoic3RyaW5nIiwiaXNzIjoiaHR0cHM6Ly9zZWN1cmV0b2tlbi5nb29nbGUuY29tL2Zpci1sb2NhdG9yLTM1ODM5IiwiYXVkIjoiZmlyLWxvY2F0b3ItMzU4MzkiLCJhdXRoX3RpbWUiOjE3MjM0MjAyMzQsInVzZXJfaWQiOiJka0QyUkh1NHBjVVRNWHdGMmZvdGY2ckZmSzMzIiwic3ViIjoiZGtEMlJIdTRwY1VUTVh3RjJmb3RmNnJGZkszMyIsImlhdCI6MTcyMzQyMDIzNCwiZXhwIjoxNzIzNDIzODM0LCJlbWFpbCI6InRlc3RlbWFpbEBnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6ZmFsc2UsImZpcmViYXNlIjp7ImlkZW50aXRpZXMiOnsiZW1haWwiOlsidGVzdGVtYWlsQGdtYWlsLmNvbSJdfSwic2lnbl9pbl9wcm92aWRlciI6InBhc3N3b3JkIn19.BrHdEDcjycdMj1hdbAtPI4r1HmXPW7cF9YwwNV_W2nH-BcYTXcmv7nK964bvXUCPOw4gSqsk7Nsgig0ATvhLr6bwOuadLjBwpXAbPc2OZNw-m6_ruINKoAyP1FGs7FvtOWNC86-ckwkIKBMB1k3-b2XRvgDeD2WhZ3bZbEAhHohjHzDatWvSIIwclHMQIPRN04b4-qXVTjtDV0zcX6pgkxTJ2XMRTgrpwoAxCNoThmRWbJjILmX-amzmdAiCjFzQW1lCP_RIR4ZOT0blLTupDxNFmdV5mj6oV7WZmH-NPO4sGmfHDoKVwoFX8s82E77p-esKUF7QkRDSCtaSQES3og",
#     #             "registered": True,
#     #             "refreshToken": "AMf-vByZFCBWektg34QkcoletyWBbPbLRccBgL32KjX04dwzTtIePkIQ5B48T9oRP9wFBF876Ts-FjBa2ZKAUSm00bxIzigAoX7yEancXdGaLXXQuqTyZ2tdCWtcac_XSd-_EpzuOiZ_6Zoy7d-Y0i14YQNRW3BdEfgkwU6tHRDZTfg0K-uQi3iorbO-9l_O4_REq-sWRTssxyXIik4vKdtrphyhhwuOUTppdRSeiZbaUGZOcJSi7Es",
#     #             "expiresIn": "3600",
#     #             "created_at": "2024-08-11T19:50:33.617798",
#     #         },
#     #     }
#     return response


# @app.post("/refresh_token", response_model=dict[Any, Any])
# async def refresh_token(req: ReqRefreshToken):
#     try:
#         # if CONF.firebase_api_key != "":
#         response = await request_handling(
#             req, ReqRefreshToken, dict[Any, Any], refresh_id_token
#         )
#         # else:
#         #     response = {
#         #         "message": "Request received",
#         #         "request_id": "req-228dc80c-e545-4cfb-ad07-b140ee7a8aac",
#         #         "data": {
#         #             "kind": "identitytoolkit#VerifyPasswordResponse",
#         #             "localId": "dkD2RHu4pcUTMXwF2fotf6rFfK33",
#         #             "email": "testemail@gmail.com",
#         #             "displayName": "string",
#         #             "idToken": "eyJhbGciOiJSUzI1NiIsImtpZCI6ImNlMzcxNzMwZWY4NmViYTI5YTUyMTJkOWI5NmYzNjc1NTA0ZjYyYmMiLCJ0eXAiOiJKV1QifQ.eyJuYW1lIjoic3RyaW5nIiwiaXNzIjoiaHR0cHM6Ly9zZWN1cmV0b2tlbi5nb29nbGUuY29tL2Zpci1sb2NhdG9yLTM1ODM5IiwiYXVkIjoiZmlyLWxvY2F0b3ItMzU4MzkiLCJhdXRoX3RpbWUiOjE3MjM0MjAyMzQsInVzZXJfaWQiOiJka0QyUkh1NHBjVVRNWHdGMmZvdGY2ckZmSzMzIiwic3ViIjoiZGtEMlJIdTRwY1VUTVh3RjJmb3RmNnJGZkszMyIsImlhdCI6MTcyMzQyMDIzNCwiZXhwIjoxNzIzNDIzODM0LCJlbWFpbCI6InRlc3RlbWFpbEBnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6ZmFsc2UsImZpcmViYXNlIjp7ImlkZW50aXRpZXMiOnsiZW1haWwiOlsidGVzdGVtYWlsQGdtYWlsLmNvbSJdfSwic2lnbl9pbl9wcm92aWRlciI6InBhc3N3b3JkIn19.BrHdEDcjycdMj1hdbAtPI4r1HmXPW7cF9YwwNV_W2nH-BcYTXcmv7nK964bvXUCPOw4gSqsk7Nsgig0ATvhLr6bwOuadLjBwpXAbPc2OZNw-m6_ruINKoAyP1FGs7FvtOWNC86-ckwkIKBMB1k3-b2XRvgDeD2WhZ3bZbEAhHohjHzDatWvSIIwclHMQIPRN04b4-qXVTjtDV0zcX6pgkxTJ2XMRTgrpwoAxCNoThmRWbJjILmX-amzmdAiCjFzQW1lCP_RIR4ZOT0blLTupDxNFmdV5mj6oV7WZmH-NPO4sGmfHDoKVwoFX8s82E77p-esKUF7QkRDSCtaSQES3og",
#         #             "registered": True,
#         #             "refreshToken": "AMf-vByZFCBWektg34QkcoletyWBbPbLRccBgL32KjX04dwzTtIePkIQ5B48T9oRP9wFBF876Ts-FjBa2ZKAUSm00bxIzigAoX7yEancXdGaLXXQuqTyZ2tdCWtcac_XSd-_EpzuOiZ_6Zoy7d-Y0i14YQNRW3BdEfgkwU6tHRDZTfg0K-uQi3iorbO-9l_O4_REq-sWRTssxyXIik4vKdtrphyhhwuOUTppdRSeiZbaUGZOcJSi7Es",
#         #             "expiresIn": "3600",
#         #             "created_at": "2024-08-11T19:50:33.617798",
#         #         },
#         #     }
#         return response
#     except Exception as e:
#         raise HTTPException(status_code=400, detail="Token refresh failed")


# @app.post("/reset_password", response_model=Dict[str, Any])
# async def reset_password_endpoint(req: ReqResetPassword):
#     response = await request_handling(
#         req, ReqResetPassword, dict[str, Any], reset_password
#     )
#     return response


# @app.post("/confirm_reset", response_model=Dict[str, Any])
# async def confirm_reset_endpoint(req: ReqConfirmReset):
#     response = await request_handling(
#         req, ReqConfirmReset, dict[str, Any], confirm_reset
#     )
#     return response


# @app.post(
#     "/change_password",
#     response_model=Dict[str, Any],
#     dependencies=[Depends(JWTBearer())],
# )
# async def change_password_endpoint(req: ReqChangePassword, request: Request):
#     response = await request_handling(
#         req, ReqChangePassword, dict[str, Any], change_password
#     )
#     return response


# @app.post(
#     "/change_email", response_model=Dict[str, Any], dependencies=[Depends(JWTBearer())]
# )
# async def change_email_endpoint(req: ReqChangeEmail, request: Request):
#     response = await request_handling(
#         req, ReqChangeEmail, dict[str, Any], change_email
#     )
#     return response
