import pytest
from unittest.mock import AsyncMock, patch

def get_document_side_effect(collection, document, res_layer_matchings_user_matching, 
                             res_layer_matchings_dataset_matching):
    if (collection , document) == ("layer_matchings", "dataset_matching"):
        return res_layer_matchings_dataset_matching
    elif (collection,document) == ("layer_matchings" , "user_matching"):
        return res_layer_matchings_user_matching
    return None

@pytest.mark.asyncio
async def test_gradient_color_based_on_zone(async_client , 
                                            user_profile_data ,
                                             res_layer_matchings_dataset_matching,
                                             res_layer_matchings_user_matching,
                                             sample_google_category_search_response,
                                             req_GradientColorBasedOnZone
                                             ):

    with (patch("storage.db", new_callable=AsyncMock) as user_layers,
          patch("backend_common.auth.db", new_callable=AsyncMock ) as user_profile,
          patch("data_fetcher.load_dataset" , new_callable=AsyncMock) as dataset_loading
                  ):
        user_profile.get_document.return_value = user_profile_data
        user_layers.get_document.side_effect = lambda collection, document: get_document_side_effect(
            collection, document, 
            res_layer_matchings_user_matching, 
            res_layer_matchings_dataset_matching
        )
        dataset_loading.return_value = sample_google_category_search_response
        response = await async_client.post("/fastapi/gradient_color_based_on_zone", json=req_GradientColorBasedOnZone)
        assert response.status_code == 200



@pytest.mark.asyncio
async def test_gradient_color_based_on_zone_nolayerfound(async_client , 
                                            user_profile_data ,
                                             res_layer_matchings_dataset_matching,
                                             res_layer_matchings_user_matching,
                                             sample_google_category_search_response,
                                             req_GradientColorBasedOnZone
                                             ):
    
    req_GradientColorBasedOnZone["request_body"]["change_lyr_id"] = "123"
    with (patch("storage.db", new_callable=AsyncMock) as user_layers,
          patch("backend_common.auth.db", new_callable=AsyncMock ) as user_profile,
          patch("data_fetcher.load_dataset" , new_callable=AsyncMock) as dataset_loading
                  ):
        user_profile.get_document.return_value = user_profile_data
        user_layers.get_document.side_effect = lambda collection, document: get_document_side_effect(
            collection, document, 
            res_layer_matchings_user_matching, 
            res_layer_matchings_dataset_matching
        )
        dataset_loading.return_value = sample_google_category_search_response
        response = await async_client.post("/fastapi/gradient_color_based_on_zone", json=req_GradientColorBasedOnZone)
        assert response.status_code == 404

