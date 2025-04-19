
import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_refresh_token(async_client , firebase_api_request_refresh_token):
    req_payload = {
            "message": "string",
            "request_info": {
                "additionalProp1": {}
            },
            "request_body": {
                "grant_type": "refresh_token",
                "refresh_token": "AMf-vBzoT0GbO4IENbpBjyUugPWV7jsOMYrvPi7gutTXCsp7KDzTmpApkUXnmnlgzw42Lbb3jQcPDhFhlKD_sKiRRNHQgyM3hYoMkg1KrpegEeKMupLaz6pEuE3IB80CQfZwfUdIYnFaA4RxhIoREoAYiiWMIANQDNEjeHZQn6JO5m8mGHVErdwXzDWxlBxBUMVn3hRyGmK-alChKCaP-KvaXxEUVfa5Lgu_A77JkE89-kw0gbgVUkU"
            }
            }
    with(patch("backend_common.auth.make_firebase_api_request" , new_callable=AsyncMock) 
         as firebase_data
         ):
        firebase_data.return_value = firebase_api_request_refresh_token
        response = await async_client.post("/fastapi/refresh-token" , json=req_payload)
        assert response.status_code == 200



@pytest.mark.asyncio
async def test_refresh_token_notsigned(async_client , firebase_sign_in):
    req_payload = {
            "message": "string",
            "request_info": {
                "additionalProp1": {}
            },
            "request_body": {
               
                "refresh_token": "AMf-vBzoT0GbO4IENbpBjyUugPWV7jsOMYrvPi7gutTXCsp7KDzTmpApkUXnmnlgzw42Lbb3jQcPDhFhlKD_sKiRRNHQgyM3hYoMkg1KrpegEeKMupLaz6pEuE3IB80CQfZwfUdIYnFaA4RxhIoREoAYiiWMIANQDNEjeHZQn6JO5m8mGHVErdwXzDWxlBxBUMVn3hRyGmK-alChKCaP-KvaXxEUVfa5Lgu_A77JkE89-kw0gbgVUkU"
            }
            }
    with(patch("backend_common.auth.make_firebase_api_request" , new_callable=AsyncMock) 
         as firebase_data
         ):
        firebase_data.return_value = firebase_sign_in
        response = await async_client.post("/fastapi/refresh-token" , json=req_payload)
        assert response.status_code == 422