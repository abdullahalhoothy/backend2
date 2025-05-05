import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import json
@pytest.mark.asyncio
async def test_save_producer_catalog(async_client, user_profile_data, req_save_producer_catlog):
    mock_bg_task = MagicMock()
    mock_bg_task.add_task = MagicMock()
    with (patch("backend_common.auth.db", new_callable=AsyncMock) as load_user_data,
          patch("backend_common.auth.get_background_tasks", return_value=mock_bg_task) as bg_task,
          patch("data_fetcher.upload_file_to_google_cloud_bucket") as mock_upload):
        
        mock_upload.return_value = "https://s-locator.com/test.png"
       
        load_user_data.get_document.return_value = user_profile_data
        response = await async_client.post(
            "/fastapi/save_producer_catalog",
            data={"req": json.dumps(req_save_producer_catlog["req_data"])},  
            files={"image": req_save_producer_catlog["image"]}  
        )
        assert response.status_code == 200

async def test_save_producer_catalog_noimage(async_client, user_profile_data, req_save_producer_catlog):
    mock_bg_task = MagicMock()
    mock_bg_task.add_task = MagicMock()
    with (patch("backend_common.auth.db", new_callable=AsyncMock) as load_user_data,
          patch("backend_common.auth.get_background_tasks", return_value=mock_bg_task) as bg_task,
          patch("data_fetcher.upload_file_to_google_cloud_bucket") as mock_upload):
        
        mock_upload.return_value = "https://s-locator.com/test.png"
       
        load_user_data.get_document.return_value = user_profile_data
        response = await async_client.post(
            "/fastapi/save_producer_catalog",
            data={"req": json.dumps(req_save_producer_catlog["req_data"])}
        )
        assert response.status_code == 500