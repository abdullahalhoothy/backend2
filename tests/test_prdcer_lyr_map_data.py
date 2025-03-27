from unittest.mock import patch, AsyncMock
import pytest


def get_document_side_effect(collection, document, 
                             res_layer_matchings_user_matching, 
                             res_layer_matchings_dataset_matching):
    if (collection, document) == ("layer_matchings", "user_matching"):
        return res_layer_matchings_user_matching
    elif (collection, document) == ("layer_matchings", "dataset_matching"):
        return res_layer_matchings_dataset_matching
    return None  

@pytest.mark.asyncio
async def test_prdcer_lyr_map_data(
    async_client, 
    res_layer_matchings_user_matching, 
    req_load_user_profile, 
    user_profile_data, 
    res_layer_matchings_dataset_matching,
    sample_google_category_search_response
):
    req_load_user_profile['request_body']['prdcer_lyr_id'] = 'le2014eaa-2330-4765-93b6-1800edd4979f'

    with (patch("storage.db", new_callable=AsyncMock) as mock_db, 
         patch("backend_common.auth.db", new_callable=AsyncMock) as mock_user_data,
         patch("data_fetcher.load_dataset", new_callable=AsyncMock) as dataset):

        # Assign the global side effect function with necessary arguments
        mock_db.get_document.side_effect = lambda collection, document: get_document_side_effect(
            collection, document, 
            res_layer_matchings_user_matching, 
            res_layer_matchings_dataset_matching
        )

        mock_user_data.get_document.return_value = user_profile_data
        dataset.return_value = sample_google_category_search_response

        response = await async_client.post("/fastapi/prdcer_lyr_map_data", json=req_load_user_profile)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_prdcer_lyr_map_data_no_lyr_found(
        async_client, 
        res_layer_matchings_user_matching, 
        req_load_user_profile, 
        user_profile_data, 
        res_layer_matchings_dataset_matching,
        sample_google_category_search_response
):

    with (patch("storage.db", new_callable=AsyncMock) as mock_db, 
         patch("backend_common.auth.db", new_callable=AsyncMock) as mock_user_data,
         patch("data_fetcher.load_dataset", new_callable=AsyncMock) as dataset):

        # Assign the global side effect function with necessary arguments
        mock_db.get_document.side_effect = lambda collection, document: get_document_side_effect(
            collection, document, 
            res_layer_matchings_user_matching, 
            res_layer_matchings_dataset_matching
        )

        mock_user_data.get_document.return_value = user_profile_data
        dataset.return_value = sample_google_category_search_response

        response = await async_client.post("/fastapi/prdcer_lyr_map_data", json=req_load_user_profile)
        assert response.status_code == 404




@pytest.mark.asyncio
async def test_prdcer_lyr_map_data_key_data(
        async_client, 
        res_layer_matchings_user_matching, 
        req_load_user_profile, 
        user_profile_data, 
        res_layer_matchings_dataset_matching,
        sample_google_category_search_response
):

    with (patch("storage.db", new_callable=AsyncMock) as mock_db, 
         patch("backend_common.auth.db", new_callable=AsyncMock) as mock_user_data,
         patch("data_fetcher.load_dataset", new_callable=AsyncMock) as dataset):
        
        req_load_user_profile['request_body']['prdcer_lyr_id'] = 'le2014eaa-2330-4765-93b6-1800edd4979f'
        mock_db.get_document.side_effect = lambda collection, document: get_document_side_effect(
            collection, document, 
            res_layer_matchings_user_matching, 
            res_layer_matchings_dataset_matching
        )

        mock_user_data.get_document.return_value = user_profile_data
        dataset.return_value = sample_google_category_search_response

        response = await async_client.post("/fastapi/prdcer_lyr_map_data", json=req_load_user_profile)
        response_data = response.json()
        assert all(key in response_data['data'] for key in  ["prdcer_layer_name", "prdcer_lyr_id", "bknd_dataset_id"])