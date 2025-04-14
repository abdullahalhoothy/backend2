import pytest
from unittest.mock import MagicMock, patch
@pytest.mark.asyncio
async def test_update_user_profile(async_client,req_load_user_profile):
    req_load_user_profile['request_body']['account_type'] = "admin"
    req_load_user_profile['request_body']['admin_id'] = "string"
    req_load_user_profile['request_body']['show_price_on_purchase'] = False
    mock_bg_tasks = MagicMock()
    mock_bg_tasks.add_task = MagicMock()
    with (patch("backend_common.auth.get_background_tasks",return_value = mock_bg_tasks ) as bg_task):
        response = await async_client.post("/fastapi/update_user_profile" , json=req_load_user_profile)
        assert response.status_code == 200
        response_data = response.json()
        assert "user_id" in response_data['data']
        assert "account_type" in response_data['data']
        assert "admin_id" in response_data["data"]
