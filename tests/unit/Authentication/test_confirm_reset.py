import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_resert_password(async_client , firebase_sign_in):
        req_payload = {
                "message": "string",
                "request_info": {},
                "request_body": {
                    "oob_code": "string",
                    "new_password": "string"
                }
                }
        with(patch("backend_common.auth.make_firebase_api_request" , new_callable=AsyncMock) 
         as firebase_data
         ):
          firebase_data.return_value = firebase_sign_in
          response = await async_client.post("/fastapi/confirm-reset" , json=req_payload)
          assert response.status_code == 200

@pytest.mark.asyncio
async def test_resert_password_failed(async_client , firebase_sign_in):
        req_payload = {
                "message": "string",
                "request_info": {},
                "request_body": {
                    "oob_code": "string",
                    # "new_password": "string"
                }
                }
        with(patch("backend_common.auth.make_firebase_api_request" , new_callable=AsyncMock) 
         as firebase_data
         ):
          firebase_data.return_value = firebase_sign_in
          response = await async_client.post("/fastapi/confirm-reset" , json=req_payload)
          assert response.status_code == 422