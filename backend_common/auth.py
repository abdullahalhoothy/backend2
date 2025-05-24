from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import Any
from fastapi import Depends, HTTPException, status, Request
from backend_common.logging_wrapper import apply_decorator_to_module
from fastapi.security import OAuth2PasswordBearer
from backend_common.dtypes.auth_dtypes import (
    ReqCreateFirebaseUser,
    ReqUserLogin,
    ReqResetPassword,
    ReqConfirmReset,
    ReqChangePassword,
    ReqRefreshToken,
    ReqChangeEmail,
    ReqCreateUserProfile,
    UserProfileSettings
)
from backend_common.common_config import CONF
from .background import get_background_tasks
import random
import requests
import os
import json
import firebase_admin
from firebase_admin import credentials, auth, firestore_async, firestore
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import stripe
import logging
from google.oauth2 import service_account
import asyncio
from fastapi import BackgroundTasks
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
stripe.api_key = CONF.stripe_api_key


class FirestoreDB:
    def __init__(self, collections_to_listen: list[str]):
        self._async_client = None
        self._sync_client = None
        self._cache = {collection: {} for collection in collections_to_listen}
        self._collection_listeners = {}
        self._collections_to_listen = collections_to_listen

    def get_async_client(self):
        if self._async_client is None:
            google_auth_creds = service_account.Credentials.from_service_account_file(
                CONF.firebase_sp_path
            )
            self._async_client = firestore_async.AsyncClient(
                credentials=google_auth_creds
            )
        return self._async_client

    def get_sync_client(self):
        if self._sync_client is None:
            self._sync_client = firestore.Client.from_service_account_json(
                CONF.firebase_sp_path
            )
        return self._sync_client

    def setup_collection_listener(self, collection_name: str):
        """Synchronous setup of collection listener"""
        if collection_name not in self._collection_listeners:
            collection_ref = self.get_sync_client().collection(collection_name)

            def on_snapshot(col_snapshot, changes, read_time):
                for change in changes:
                    doc_id = change.document.id
                    if change.type.name in ["ADDED", "MODIFIED"]:
                        data = change.document.to_dict()
                        self._cache[collection_name][doc_id] = data
                        logger.info(
                            f"Cache updated for {collection_name} document {doc_id}"
                        )
                    elif change.type.name == "REMOVED":
                        self._cache[collection_name].pop(doc_id, None)
                        logger.info(
                            f"Removed {collection_name} document {doc_id} from cache"
                        )

            # Watch the collection
            self._collection_listeners[collection_name] = collection_ref.on_snapshot(
                on_snapshot
            )
            logger.info(f"Started listener for collection {collection_name}")

    async def get_document(self, collection_name: str, doc_id: str) -> dict:
        if collection_name not in self._cache:
            raise ValueError(f"Collection {collection_name} is not being monitored")

        if doc_id in self._cache[collection_name]:
            logger.info(f"Retrieved {collection_name} document {doc_id} from cache")
            return self._cache[collection_name][doc_id]

        doc_ref = self.get_async_client().collection(collection_name).document(doc_id)
        doc = await doc_ref.get()

        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document not found in {collection_name}",
            )

        data = doc.to_dict()
        self._cache[collection_name][doc_id] = data
        return data

    async def initialize_collection_cache(self, collection_name: str):
        collection_ref = self.get_async_client().collection(collection_name)
        docs = await collection_ref.get()
        for doc in docs:
            self._cache[collection_name][doc.id] = doc.to_dict()
        logger.info(
            f"Initialized cache for {collection_name} with {len(docs)} documents"
        )

    async def initialize_all(self):
        """Initialize all caches and setup listeners"""
        # Initialize caches asynchronously
        for collection_name in self._collections_to_listen:
            await self.initialize_collection_cache(collection_name)

        # Setup listeners synchronously in a thread
        def setup_listeners():
            for collection_name in self._collections_to_listen:
                self.setup_collection_listener(collection_name)

        # Run synchronous listeners setup in a thread
        await asyncio.get_event_loop().run_in_executor(None, setup_listeners)

    def cleanup(self):
        """Synchronous cleanup of listeners with proper thread shutdown"""
        # First unsubscribe all listeners
        for listener in self._collection_listeners.values():
            if listener:
                listener.unsubscribe()

        # Give threads time to exit gracefully
        time.sleep(1)  # Wait for threads to process unsubscribe

        # Clear collections
        self._collection_listeners.clear()
        self._cache.clear()

        # Close clients
        if self._async_client:
            self._async_client.close()
        if self._sync_client:
            self._sync_client.close()

db = None
# Initialize Firebase admin with firebase credentials
if os.path.exists(CONF.firebase_sp_path):
    firebase_creds = credentials.Certificate(CONF.firebase_sp_path)
    default_app = firebase_admin.initialize_app(firebase_creds)
    # Create Firestore client with google-auth credentials
    db = FirestoreDB(CONF.firestore_collections)


class JWTBearer(HTTPBearer):
    """This class is to make endpoints secure with JWT"""

    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        self.request = request
        credentials_obj: HTTPAuthorizationCredentials = await super(
            JWTBearer, self
        ).__call__(request)
        if credentials_obj:
            if not credentials_obj.scheme == "Bearer":
                raise HTTPException(
                    status_code=403, detail="Invalid authentication scheme."
                )
            if not await self.verify_jwt(credentials_obj.credentials):
                raise HTTPException(
                    status_code=403, detail="Invalid token or expired token."
                )
            return credentials_obj.credentials
        else:
            raise HTTPException(status_code=403, detail="Invalid authorization code.")

    async def verify_jwt(self, jwt_token: str) -> bool:
        decoded_token = my_verify_id_token(jwt_token)
        token_user_id = decoded_token["uid"]

        # Handle both JSON and form data
        content_type = self.request.headers.get("content-type", "")

        if "multipart/form-data" in content_type:
            # For multipart form data, get the form first
            form = await self.request.form()
            # Check if there's a JSON string in the form data
            if "data" in form:
                try:
                    request_data = json.loads(form["data"])
                    user_id = request_data.get("request_body", {}).get("user_id")
                except json.JSONDecodeError:
                    return False
            else:
                # Direct form fields
                user_id = form.get("user_id")
        else:
            # Regular JSON request
            try:
                request_body = await self.request.json()
                user_id = request_body.get("user_id")
            except json.JSONDecodeError:
                return False

        if user_id and token_user_id != user_id:
            return False
        return True


async def create_firebase_user(req: ReqCreateFirebaseUser) -> dict[str, Any]:
    try:
        # Create user in Firebase
        user = auth.create_user(
            email=req.email, password=req.password, display_name=req.username
        )

        # Send user verify email
        payload = {
            "email": req.email,
            "password": req.password,
            "returnSecureToken": True,
        }
        response = await make_firebase_api_request(
            CONF.firebase_signInWithPassword, payload
        )

        ## Send Verifiy Email
        payload = {"requestType": "VERIFY_EMAIL", "idToken": response["idToken"]}
        _ = await make_firebase_api_request(CONF.firebase_sendOobCode, payload=payload)
        return {"user_id": user.uid, "message": "User profile created successfully"}
    except auth.EmailAlreadyExistsError as emialerrror:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already taken",
        ) from emialerrror


async def login_user(req: ReqUserLogin) -> dict[str, Any]:
    try:
        payload = {
            "email": req.email,
            "password": req.password,
            "returnSecureToken": True,
        }
        response = await make_firebase_api_request(
            CONF.firebase_signInWithPassword, payload
        )
        response["created_at"] = datetime.now()
        if response.get("localId", "") != "":
            user = auth.get_user(response["localId"])
            if user.email_verified:
                return response
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Unverified Email"
                )
        raise auth.UserNotFoundError(message="")
    except auth.UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        ) from e


async def refresh_id_token(req: ReqRefreshToken) -> dict[str, Any]:
    try:
        payload = {"grant_type": req.grant_type, "refresh_token": req.refresh_token}
        response = await make_firebase_api_request(CONF.firebase_refresh_token, payload)
        response["created_at"] = datetime.now()
        response["idToken"] = response["id_token"]
        response["refreshToken"] = response["refresh_token"]
        response["expiresIn"] = response["expires_in"]
        response["localId"] = response["user_id"]
        # drop certain keys from reponse like id_token, refresh_token, expires_in, user_id
        keys_to_drop = ["id_token", "refresh_token", "expires_in", "user_id"]
        response = {
            key: value for key, value in response.items() if key not in keys_to_drop
        }
        return response
    except auth.UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        ) from e


def my_verify_id_token(token: str = Depends(oauth2_scheme)):
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


async def reset_password(req: ReqResetPassword) -> dict[str, Any]:
    payload = {"requestType": "PASSWORD_RESET", "email": req.email}
    response = await make_firebase_api_request(CONF.firebase_sendOobCode, payload)
    return response


async def confirm_reset(req: ReqConfirmReset) -> dict[str, Any]:
    payload = {"oobCode": req.oob_code, "newPassword": req.new_password}
    response = await make_firebase_api_request(CONF.firebase_resetPassword, payload)
    return response


async def change_password(req: ReqChangePassword) -> dict[str, Any]:
    login_req = ReqUserLogin(email=req.email, password=req.password)
    response = await login_user(login_req)
    if response.get("localId", "") != req.user_id:
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


async def change_email(req: ReqChangeEmail) -> dict[str, Any]:
    login_req = ReqUserLogin(email=req.current_email, password=req.password)
    response = await login_user(login_req)
    if response.get("localId", "") != req.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User id did not match firebase user ID acquired from user name and password",
        )

    ## Send vertification to the new email
    payload = {
        "requestType": "VERIFY_AND_CHANGE_EMAIL",
        "idToken": response["idToken"],
        "newEmail": req.new_email,
    }
    _ = await make_firebase_api_request(CONF.firebase_sendOobCode, payload=payload)

    return response


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


async def get_user_email_and_username(user_id: str):
    try:
        user = auth.get_user(user_id)
        email = user.email
        username = user.display_name
        return email, username
    except auth.UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


async def save_customer_mapping(firebase_uid: str, stripe_customer_id: str):
    # Update cache immediately
    collection_name = "firebase_stripe_mappings"
    db._cache[collection_name][firebase_uid] = {
        "stripe_customer_id": stripe_customer_id
    }

    async def _background_save():
        doc_ref = (
            db.get_async_client().collection(collection_name).document(firebase_uid)
        )
        await doc_ref.set({"stripe_customer_id": stripe_customer_id})

    get_background_tasks().add_task(_background_save)
    return {"stripe_customer_id": stripe_customer_id}


async def get_stripe_customer_id(firebase_uid: str) -> str:
    try:
        data = await db.get_document("firebase_stripe_mappings", firebase_uid)
        return data["stripe_customer_id"]
    except HTTPException as e:
        if e.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stripe customer not found for this user",
            )
        raise e


async def create_user_profile(req: ReqCreateUserProfile):
    collection_name = "all_user_profiles"

    # Validate member accounts must have an admin
    if req.account_type == "member" and not req.admin_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Member accounts must have an associated administrator"
        )
    
    user_data = {
        "user_id": req.user_id,
        "email": req.email,
        "username": req.username,
        "account_type": req.account_type,
        "admin_id": req.admin_id,
        "settings": {
            "show_price_on_purchase": req.show_price_on_purchase if req.account_type == "admin" else False
        },
        "prdcer": {
            "prdcer_dataset": {
                "dataset_plan": "",
                "progress": random.randint(0, 100),
                "dataset_next_refresh_date": datetime.now() + relativedelta(months=3),
                "auto_refresh": True,
            },
            "prdcer_lyrs": {},
            "prdcer_ctlgs": {},
            "draft_ctlgs": {},
        },
    }

    # Update cache immediately
    db._cache[collection_name][req.user_id] = user_data

    async def _background_create():
        doc_ref = (
            db.get_async_client().collection(collection_name).document(req.user_id)
        )
        await doc_ref.set(user_data)

    get_background_tasks().add_task(_background_create)
    return user_data


async def update_user_profile(user_id: str, user_data: dict):
    collection_name = "all_user_profiles"

    if not user_id or user_data.get("user_id", "").strip() == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user_id: user_id cannot be empty"
        )
    
    existing_data = db._cache[collection_name].get(user_id, {})
    prdcer_data = user_data.get("prdcer", {})
    existing_prdcer = existing_data.get("prdcer", {})
    
    # Update prdcer_dataset
    prdcer_dataset = existing_prdcer.get("prdcer_dataset", {}).copy()
    for key, value in prdcer_data.get("prdcer_dataset", {}).items():
        if key:  # Simplified null/empty check
            prdcer_dataset[key] = value

    # Profile-specific update data
    update_data = {
        "user_id": user_data["user_id"],
        "prdcer": {
            "prdcer_dataset": prdcer_dataset,
            "prdcer_lyrs": prdcer_data.get("prdcer_lyrs", existing_prdcer.get("prdcer_lyrs", {})),
            "prdcer_ctlgs": prdcer_data.get("prdcer_ctlgs", existing_prdcer.get("prdcer_ctlgs", {})),
            "draft_ctlgs": prdcer_data.get("draft_ctlgs", existing_prdcer.get("draft_ctlgs", {})),
        }
    }
    merged_data = {**existing_data, **update_data}
    db._cache[collection_name][user_id] = merged_data


    async def _background_update():
        doc_ref = db.get_async_client().collection(collection_name).document(user_id)
        # Use Firestore's update instead of set to only update specified fields
        await doc_ref.update(merged_data)

    get_background_tasks().add_task(_background_update)
    return merged_data


async def update_user_profile_settings(settings_data: UserProfileSettings):
    collection_name = "all_user_profiles"
    user_id = settings_data.user_id

    existing_data = db._cache[collection_name].get(user_id, {})
    
    # Merge existing settings with new settings
    existing_settings = existing_data.get("settings", {})
    merged_settings = {
        **existing_settings,
        "show_price_on_purchase": settings_data.show_price_on_purchase
    }

    # Create update data with proper structure
    update_data = {
        "user_id": user_id,
        "account_type": settings_data.account_type,
        "admin_id": settings_data.admin_id,
        "settings": merged_settings
    }

    # Preserve existing data while applying updates
    merged_data = {**existing_data, **update_data}
    db._cache[collection_name][user_id] = merged_data

    async def _background_update():
        doc_ref = db.get_async_client().collection(collection_name).document(user_id)
        # Use Firestore's update instead of set to only update specified fields
        await doc_ref.update(merged_data)

    get_background_tasks().add_task(_background_update)
    return merged_data


async def load_user_profile(user_id: str) -> dict:
    """
    Loads user data from Firestore based on the user ID.
    If the user doesn't exist, creates an empty profile.
    """
    try:
        return await db.get_document("all_user_profiles", user_id)
    except HTTPException as e:
        if e.status_code == status.HTTP_404_NOT_FOUND:
            req = ReqCreateUserProfile(
                user_id="temp", username="", password="", email=""
            )
            return await create_user_profile(req)
        raise e


# Apply the decorator to all functions in this module
apply_decorator_to_module(logger)(__name__)