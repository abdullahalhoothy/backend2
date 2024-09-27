from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from all_types.myapi_dtypes import (
    ReqCreateUserProfile,
    ReqUserLogin,
    ReqUserProfile,
    ReqResetPassword,
    ReqConfirmReset,
    ReqChangePassword,
    ReqRefreshToken,
    ReqChangeEmail
)
from storage import load_user_profile, update_user_profile
from jose import jwt, JWTError
import requests
import os
from firebase_admin import auth
import firebase_admin
from firebase_admin import credentials
from config_factory import get_conf
import time


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

CONF = get_conf()
if os.path.exists(CONF.firebase_sp_path):
    cred = credentials.Certificate(CONF.firebase_sp_path)
    default_app = firebase_admin.initialize_app(cred)





async def create_user_profile(req: ReqCreateUserProfile) -> Dict[str, str]:
    try:
        # Create user in Firebase
        user = auth.create_user(
            email=req.email, password=req.password, display_name=req.username
        )

        user_data = {
            "user_id": user.uid,
            "username": req.username,
            "email": req.email,
            "prdcer": {"prdcer_dataset": {}, "prdcer_lyrs": {}, "prdcer_ctlgs": {},"draft_ctlgs":{}},
        }

        # Save additional user data to your database
        update_user_profile(user.uid, user_data)

        # Send user verify email

        payload = {
            "email": req.email,
            "password": req.password,
            "returnSecureToken": True,
        }
        response = await make_firebase_api_request(CONF.firebase_signInWithPassword, payload)

        ## Send Verifiy Email
        payload = {
            "requestType" : "VERIFY_EMAIL",
            "idToken": response['idToken']
        }
        response = await make_firebase_api_request(CONF.firebase_send_verify_email,payload=payload)
        return {"user_id": user.uid, "message": "User profile created successfully"}
    except auth.EmailAlreadyExistsError as emialerrror:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already taken",
        ) from emialerrror



async def login_user(req: ReqUserLogin) -> Dict[str, str]:
    try:
        payload = {
            "email": req.email,
            "password": req.password,
            "returnSecureToken": True,
        }
        response = await make_firebase_api_request(CONF.firebase_signInWithPassword, payload)
        response["created_at"] = datetime.now()
        if response.get('localId','null') != 'null':
            user = auth.get_user(response['localId'])
            if user.email_verified:
                return response
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unverified Email"
                )
        raise auth.UserNotFoundError(message="")
    except auth.UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        ) from e

#######################################################################################
async def refresh_id_token(req:ReqRefreshToken) -> Dict[str, str]:
    try:
        payload = {
            "grant_type" :req.grant_type,
            "refresh_token" : req.refresh_token
        }
        response = await make_firebase_api_request(CONF.firebase_refresh_token,payload)
        response["created_at"] = datetime.now()
        return response
    except auth.UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        ) from e

########################################################################################

async def my_verify_id_token(token: str = Depends(oauth2_scheme)):
    try:
        return auth.verify_id_token(token)
    except auth.InvalidIdTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"invalid access token={token}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e




async def get_user_account(req: ReqUserProfile) -> Dict[str, Any]:
    user_data = load_user_profile(req.user_id)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return user_data



async def reset_password(req: ReqResetPassword) -> Dict[str, str]:
    payload = {"requestType": "PASSWORD_RESET", "email": req.email}
    response = await make_firebase_api_request(CONF.firebase_sendOobCode, payload)
    return response



async def confirm_reset(req: ReqConfirmReset) -> Dict[str, str]:
    payload = {"oobCode": req.oob_code, "newPassword": req.new_password}
    response = await make_firebase_api_request(CONF.firebase_resetPassword, payload)
    return response



async def change_password(req: ReqChangePassword) -> Dict[str, str]:
    login_req = ReqUserLogin(email=req.email,password=req.password)
    response = await login_user(login_req)
    if response.get("localId","Null") != req.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User id did not match firebase user ID acquired from user name and password",
        ) 

    # Now change the password
    payload = {
        "idToken": response["idToken"],
        "password": req.new_password,
        "returnSecureToken": True,
    }
    response = await make_firebase_api_request(CONF.firebase_update, payload)

    return response

async def change_email(req: ReqChangeEmail) -> Dict[str, str]:
    login_req = ReqUserLogin(email=req.current_email,password=req.password)
    response = await login_user(login_req)
    if response.get('localId',"Null") != req.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User id did not match firebase user ID acquired from user name and password",
        ) 

    payload = {
        "idToken": response['idToken'],
        "email": req.new_email,
        "returnSecureToken": True,
    }

    response = await make_firebase_api_request(CONF.firebase_update, payload)

    ## Send vertification email
    payload = {
            "requestType" : "VERIFY_EMAIL",
            "idToken": response['idToken']
        }
    output_not_needed = await make_firebase_api_request(CONF.firebase_send_verify_email,payload=payload)

    return response


#################################################################################### Confirm testing

####################################################################################

async def make_firebase_api_request(url, payload):
    try:
        url = url + CONF.firebase_api_key
        response = requests.post(url, json=payload, timeout=120)
        return response.json()
    except requests.exceptions.HTTPError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=e.response.json().get("error", {}).get("message"),
        ) from e

        
