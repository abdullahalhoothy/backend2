import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from firebase_admin import auth
@pytest.mark.asyncio
async def test_change_password(async_client , req_auth_user_data, firebase_sign_in):
    data_payload = {
        "message": "string",
        "request_info": {},
        "request_body": {
            "email": "sharif@gmail.com",
            "password": "123",
            "user_id": "sUEGmzrKaOW3hBcaOKM73HJLTRa2",
            "new_password": "string"
        }
    }
    mock_user = MagicMock(**{
        "localId": req_auth_user_data["localId"],
        "email": req_auth_user_data["email"],
        "display_name": req_auth_user_data["displayName"],
        "email_verified": req_auth_user_data["emailVerified"],
        "disabled": req_auth_user_data["disabled"],
        "provider_data": req_auth_user_data["providerUserInfo"]
    })
    mock_user.metadata = MagicMock(
        creation_timestamp=int(req_auth_user_data["createdAt"]),
        last_sign_in_timestamp=int(req_auth_user_data["lastLoginAt"])
    )

    with (patch("backend_common.auth.make_firebase_api_request", new_callable=AsyncMock) as firebase_data,
          patch.object(auth, "get_user", return_value=mock_user) as mock_get_user
    ):
           firebase_data.return_value = firebase_sign_in
           response = await async_client.post("/fastapi/change-password" , json=data_payload)
           assert response.status_code == 200


@pytest.mark.asyncio
async def test_change_password_userid_mismatch(async_client , req_auth_user_data, firebase_sign_in):
    data_payload = {
        "message": "string",
        "request_info": {},
        "request_body": {
            "email": "sharif@gmail.com",
            "password": "123",
            "user_id": "sUEGmz",
            "new_password": "string"
        }
    }
    mock_user = MagicMock(**{
        "localId": req_auth_user_data["localId"],
        "email": req_auth_user_data["email"],
        "display_name": req_auth_user_data["displayName"],
        "email_verified": req_auth_user_data["emailVerified"],
        "disabled": req_auth_user_data["disabled"],
        "provider_data": req_auth_user_data["providerUserInfo"]
    })
    mock_user.metadata = MagicMock(
        creation_timestamp=int(req_auth_user_data["createdAt"]),
        last_sign_in_timestamp=int(req_auth_user_data["lastLoginAt"])
    )

    with (patch("backend_common.auth.make_firebase_api_request", new_callable=AsyncMock) as firebase_data,
          patch.object(auth, "get_user", return_value=mock_user) as mock_get_user
    ):
           firebase_data.return_value = firebase_sign_in
           response = await async_client.post("/fastapi/change-password" , json=data_payload)
           assert response.status_code == 401