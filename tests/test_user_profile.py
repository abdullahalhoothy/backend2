import pytest
from unittest.mock import patch,AsyncMock


@pytest.mark.asyncio
async def test_get_user_profile_endpoint(async_client, user_profile_data , req_load_user_profile):


    with ( patch("backend_common.auth.db.get_document", new_callable=AsyncMock) as mock_load_user_profile):

        mock_load_user_profile.return_value =  user_profile_data
        response = await async_client.post("/fastapi/user_profile",   json=req_load_user_profile)
        assert response.status_code == 200
        response_data = response.json()
        print(response)
        assert "message" in response_data
        assert "request_id" in response_data
        assert "data" in response_data

@pytest.mark.asyncio
async def test_user_profile_endpoint_fail(async_client, user_profile_data , req_load_user_profile_duplicate):
    """" Testing the response when user_id missing """

    with (patch("backend_common.auth.db.get_document" , new_callable=AsyncMock) as mock_load_user_profile):
        mock_load_user_profile.return_value = user_profile_data
        response = await async_client.post("/fastapi/user_profile", json=req_load_user_profile_duplicate)
        assert response.status_code == 422

