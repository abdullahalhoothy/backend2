import pytest
from unittest.mock import patch
@pytest.mark.asyncio
async def test_process_llm_query(async_client, res_country_city, req_llm_query, res_llm_query):
    with (
        patch("fetch_dataset_llm.fetch_approved_data", return_value=res_country_city) as city_data,
        patch("fetch_dataset_llm.ChatOpenAI.invoke", return_value=res_llm_query['content']) as mock_model
    ):
        response = await async_client.post("/fastapi/process_llm_query", json=req_llm_query)
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_process_llm_query_fileds(async_client, res_country_city, req_llm_query, res_llm_query):
    with (
        patch("fetch_dataset_llm.fetch_approved_data", return_value=res_country_city) as city_data,
        patch("fetch_dataset_llm.ChatOpenAI.invoke", return_value=res_llm_query['content']) as mock_model
    ):
        response = await async_client.post("/fastapi/process_llm_query", json=req_llm_query)
        response_data = response.json()
        data = response_data["data"]
        assert "query" in data
        assert "is_valid" in data
        assert "reason" in data
        assert "endpoint" in data
        