from unittest.mock import AsyncMock, patch, MagicMock
import pytest

@pytest.mark.asyncio
async def test_delete_producer_catalog(async_client,user_profile_data,req_load_user_profile,producer_catalog_data):

    req_load_user_profile['request_body']['prdcer_ctlg_id'] = "string"
    user_profile_data['prdcer']['prdcer_ctlgs'][producer_catalog_data['prdcer_ctlg_id']] = producer_catalog_data
    mock_bg_task = MagicMock()
    mock_bg_task.add_task = MagicMock()
    with(patch("backend_common.auth.db", new_callable=AsyncMock) as load_user_profile,
         patch("data_fetcher.delete_file_from_google_cloud_bucket") as delete_file,
         patch("backend_common.auth.get_background_tasks" , return_value=mock_bg_task) as bg_tasks
         ):
        load_user_profile.get_document.return_value = user_profile_data
        response = await async_client.request("DELETE","/fastapi/delete_producer_catalog",json=req_load_user_profile)
        assert response.status_code == 200
        

@pytest.mark.asyncio
async def test_delete_producer_catalog_notfound(async_client,user_profile_data,req_load_user_profile):

    req_load_user_profile['request_body']['prdcer_ctlg_id'] = "string"
    mock_bg_task = MagicMock()
    mock_bg_task.add_task = MagicMock()
    with(patch("backend_common.auth.db", new_callable=AsyncMock) as load_user_profile,
         patch("data_fetcher.delete_file_from_google_cloud_bucket") as delete_file,
         patch("backend_common.auth.get_background_tasks" , return_value=mock_bg_task) as bg_tasks
         ):
        load_user_profile.get_document.return_value = user_profile_data
        response = await async_client.request("DELETE","/fastapi/delete_producer_catalog",json=req_load_user_profile)
        assert response.status_code == 500
