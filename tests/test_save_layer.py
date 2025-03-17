import logging

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.mark.asyncio
async def test_save_layer(async_client, req_save_layer, user_profile_data):
    with (
        patch("data_fetcher.update_user_profile", new_callable=AsyncMock) as mock_fetch,
        patch("data_fetcher.update_dataset_layer_matching", new_callable=AsyncMock) as mock_strip,
        patch("data_fetcher.update_user_layer_matching", new_callable=AsyncMock) as mock_stripe_cust,
        patch("backend_common.auth.db.get_document", new_callable=AsyncMock) as mock_user_data,
    ):
        mock_user_data.return_value = user_profile_data
        response = await async_client.post("/fastapi/save_layer", json=req_save_layer)
        # Assert response status and structure
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_save_layer(async_client, req_save_layer_duplicate, user_profile_data):
    with (
        patch("data_fetcher.update_user_profile", new_callable=AsyncMock) as mock_fetch,
        patch("data_fetcher.update_dataset_layer_matching", new_callable=AsyncMock) as mock_strip,
        patch("data_fetcher.update_user_layer_matching", new_callable=AsyncMock) as mock_stripe_cust,
        patch("backend_common.auth.db", new_callable=AsyncMock) as mock_user_data,
    ):
        mock_user_data.get_document.return_value = user_profile_data
        response = await async_client.post("/fastapi/save_layer", json=req_save_layer_duplicate)
        # Assert response status and structure
        assert response.status_code == 400
