from unittest.mock import AsyncMock, patch
import pytest 

@pytest.mark.asyncio
async def test_user_catalogs(async_client,user_profile_data, req_load_user_profile):
    with (patch("backend_common.auth.db", new_callable=AsyncMock) as load_user_data):
        load_user_data.get_document.return_value = user_profile_data
        response = await async_client.post("/fastapi/user_catalogs", json=req_load_user_profile)
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_user_catalogs_user_notfound(async_client,user_profile_data, req_load_user_profile_duplicate):
    with (patch("backend_common.auth.db", new_callable=AsyncMock) as load_user_data):
        load_user_data.get_document.return_value = user_profile_data
        response = await async_client.post("/fastapi/user_catalogs", json=req_load_user_profile_duplicate)
        assert response.status_code == 422