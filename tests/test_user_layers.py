import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_getting_user_layers(async_client , user_profile_data , req_load_user_profile):
     
    with (patch("backend_common.auth.db" , new_callable=AsyncMock) as mock_load_user_profil):
        mock_load_user_profil.get_document.return_value = user_profile_data
        response = await async_client.post("/fastapi/user_layers" , json=req_load_user_profile)
        print(response.json())
        assert response.status_code == 200 

@pytest.mark.asyncio
async def test_getting_user_layers_key_missing(async_client , user_profile_data , req_load_user_profile):

        with (patch("backend_common.auth.db.get_document" , new_callable=AsyncMock) as mock_load_user_profil):
          mock_load_user_profil.return_value = user_profile_data
          response = await async_client.post("/fastapi/user_layers" , json=req_load_user_profile)
          assert response.status_code == 500

@pytest.mark.asyncio
async def test_getting_user_layers_user_not_found(async_client , user_profile_data , req_load_user_profile_duplicate):

        with (patch("backend_common.auth.db.get_document" , new_callable=AsyncMock) as mock_load_user_profil):
          mock_load_user_profil.return_value = user_profile_data
          response = await async_client.post("/fastapi/user_layers" , json=req_load_user_profile_duplicate)
          assert response.status_code == 422

        
          
