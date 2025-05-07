import pytest
from unittest.mock import AsyncMock, patch

def get_document_side_effect(collection, document, res_layer_matchings_user_matching, 
                             res_layer_matchings_dataset_matching):
    if (collection , document) == ("layer_matchings", "dataset_matching"):
        return res_layer_matchings_dataset_matching
    elif (collection,document) == ("layer_matchings" , "user_matching"):
        return res_layer_matchings_user_matching
    return None
@pytest.fixture
def req_gadientcolorBasedOnZone():
    return {
        "message": "request from front end",
        "request_info" : {},
        "request_body":{
            "change_lyr_id": "change_lyr_id",
            "based_on_lyr_id": "base_lyr_id",
            "color_based_on": "rating" # or user_ratings_total
        
        }                     
    }
@pytest.mark.asyncio
async def test_gradient_color_based_on_zone(async_client, 
                                           user_profile_data,
                                           res_layer_matchings_dataset_matching,
                                           res_layer_matchings_user_matching,
                                           sample_google_category_search_response,
                                           req_gadientcolorBasedOnZone):  # Add the fixture as parameter
    
    with (patch("storage.db", new_callable=AsyncMock) as user_layers,
          patch("backend_common.auth.db", new_callable=AsyncMock) as user_profile,
          patch("data_fetcher.load_dataset", new_callable=AsyncMock) as dataset_loading):
        user_profile.get_document.return_value = user_profile_data
        user_layers.get_document.side_effect = lambda collection, document: get_document_side_effect(
            collection, document, 
            res_layer_matchings_user_matching, 
            res_layer_matchings_dataset_matching
        )
        dataset_loading.return_value = sample_google_category_search_response
        response = await async_client.post("/fastapi/gradient_color_based_on_zone", json=req_gadientcolorBasedOnZone)  # Now this is the actual dict
        print("mocked", user_layers.get_document.call_count)
        assert response.status_code == 200
        response_data = response.json()
        # Basic response structure validation           
        assert "data" in response_data
        
        data_returned = response_data['data']['ResGradientColorBasedOnZone']
        
        assert "type" in data_returned
        assert "features" in data_returned
        assert "properties" in data_returned
        assert "prdcer_layer_name" in data_returned
        assert "prdcer_lyr_id" in data_returned
        assert "sub_lyr_id" in data_returned
        assert "bknd_dataset_id" in data_returned
        assert "points_color" in data_returned
        assert "layer_legend" in data_returned
        assert "layer_description" in data_returned
        assert "records_count" in data_returned
        assert "city_name" in data_returned
        assert "is_zone_lyr" in data_returned
