import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_getting_user_layers(async_client , user_profile_data , req_load_user_profile , res_layer_matchings_dataset_matching):
     
    with (patch("backend_common.auth.db" , new_callable=AsyncMock) as mock_load_user_profil,
          patch("storage.db.get_document" , new_callable=AsyncMock) as load_user_layers ):
        mock_load_user_profil.get_document.return_value = user_profile_data
        load_user_layers.return_value = res_layer_matchings_dataset_matching
        response = await async_client.post("/fastapi/user_layers" , json=req_load_user_profile)
        assert response.status_code == 200 

@pytest.mark.asyncio
async def test_getting_user_layers_key_missing(async_client , user_profile_data , req_load_user_profile, res_layer_matchings_dataset_matching):

        with (patch("backend_common.auth.db" , new_callable=AsyncMock) as mock_load_user_profil,
          patch("storage.db.get_document" , new_callable=AsyncMock) as load_user_layers ):
          mock_load_user_profil.get_document.return_value = user_profile_data
          load_user_layers.return_value = res_layer_matchings_dataset_matching
          response = await async_client.post("/fastapi/user_layers" , json=req_load_user_profile)
          response_data = response.json()
          assert response.status_code == 200
          assert 'prdcer_layer_name' in response_data['data'][0]

@pytest.mark.asyncio
async def test_getting_user_layers_user_not_found(async_client , user_profile_data , req_load_user_profile_duplicate , res_layer_matchings_dataset_matching):

        with (patch("backend_common.auth.db" , new_callable=AsyncMock) as mock_load_user_profil,
              patch("storage.db.get_document", new_callable=AsyncMock) as load_user_layers):
          mock_load_user_profil.get_document.return_value = user_profile_data
          load_user_layers.return_value = res_layer_matchings_dataset_matching
          response = await async_client.post("/fastapi/user_layers" , json=req_load_user_profile_duplicate)
          assert response.status_code == 422

        
          
