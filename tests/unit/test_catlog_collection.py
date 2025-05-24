import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_fetch_catlog_collection(async_client, res_catlog_collection):

    with patch("fastapi_app.fetch_catlog_collection", new_callable=AsyncMock) as mock_load_catlog:
        catlog_collection_data = res_catlog_collection["data"]
        mock_load_catlog.return_value = catlog_collection_data
        response = await async_client.get("/fastapi/catlog_collection")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_fetch_catlog_collection_matched_data(async_client, res_catlog_collection):

    with patch("fastapi_app.fetch_catlog_collection", new_callable=AsyncMock) as mock_load_catlog:
        catlog_collection_data = res_catlog_collection["data"]
        mock_load_catlog.return_value = catlog_collection_data
        response = await async_client.get("/fastapi/catlog_collection")
        response_data = response.json()
        assert response_data["data"][0]["id"] == "2"

