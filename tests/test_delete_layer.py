import pytest
from unittest.mock import AsyncMock, patch, MagicMock

def get_document_side_effect(collection, document, 
                             res_layer_matchings_user_matching, 
                             res_layer_matchings_dataset_matching):
    if (collection, document) == ("layer_matchings", "user_matching"):
        return res_layer_matchings_user_matching
    elif (collection, document) == ("layer_matchings", "dataset_matching"):
        return res_layer_matchings_dataset_matching
    return None  

@pytest.mark.asyncio
async def test_delete_layer(async_client, res_layer_matchings_dataset_matching, user_profile_data, req_load_user_profile, res_layer_matchings_user_matching):
    req_load_user_profile['request_body']['prdcer_lyr_id'] = 'le2014eaa-2330-4765-93b6-1800edd4979f'
    mock_bg_tasks = MagicMock()
    mock_bg_tasks.add_task = MagicMock()
    with (patch("storage.db", new_callable=AsyncMock) as load_dataset,
        patch("backend_common.auth.db", new_callable=AsyncMock) as loda_user_profile,
        patch("backend_common.auth.get_background_tasks",return_value = mock_bg_tasks ) as bg_task,
        patch("storage.get_background_tasks", return_value = mock_bg_tasks) as del_bg_task
        ):
        load_dataset.get_document.side_effect = lambda collection, document: get_document_side_effect(
            collection, document, 
            res_layer_matchings_user_matching, 
            res_layer_matchings_dataset_matching
        )

        loda_user_profile.get_document.return_value = user_profile_data
        
        response = await async_client.request("DELETE","/fastapi/delete_layer", json=req_load_user_profile)
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_delete_layer_notfound(async_client, res_layer_matchings_dataset_matching, user_profile_data, req_load_user_profile):
    req_load_user_profile['request_body']['prdcer_lyr_id'] = 'le2014eaa-2330-4765-93b6-1800edd4979f'
    mock_bg_tasks = MagicMock()
    mock_bg_tasks.add_task = MagicMock()
    with (patch("storage.db", new_callable=AsyncMock) as load_dataset,
        patch("backend_common.auth.db", new_callable=AsyncMock) as loda_user_profile,
        patch("backend_common.auth.get_background_tasks",return_value = mock_bg_tasks ) as bg_task,
        patch("storage.get_background_tasks", return_value = mock_bg_tasks) as del_bg_task
        ):
        load_dataset.get_document.return_value = res_layer_matchings_dataset_matching

        loda_user_profile.get_document.return_value = user_profile_data
        
        response = await async_client.request("DELETE","/fastapi/delete_layer", json=req_load_user_profile)
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_layer_idmismatch(async_client, res_layer_matchings_dataset_matching, user_profile_data, req_load_user_profile , res_layer_matchings_user_matching):
    req_load_user_profile['request_body']['prdcer_lyr_id'] = 'string'
    mock_bg_tasks = MagicMock()
    mock_bg_tasks.add_task = MagicMock()
    with (patch("storage.db", new_callable=AsyncMock) as load_dataset,
        patch("backend_common.auth.db", new_callable=AsyncMock) as loda_user_profile,
        patch("backend_common.auth.get_background_tasks",return_value = mock_bg_tasks ) as bg_task,
        patch("storage.get_background_tasks", return_value = mock_bg_tasks) as del_bg_task
        ):
        load_dataset.get_document.side_effect = lambda collection, document: get_document_side_effect(
            collection, document, 
            res_layer_matchings_user_matching, 
            res_layer_matchings_dataset_matching
        )


        loda_user_profile.get_document.return_value = user_profile_data
        
        response = await async_client.request("DELETE","/fastapi/delete_layer", json=req_load_user_profile)
        assert response.status_code == 500