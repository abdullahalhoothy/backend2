import logging

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.mark.asyncio
async def test_fetch_dataset_real_estate(async_client, req_fetch_dataset_real_estate, sample_real_estate_response):
    with patch("data_fetcher.get_real_estate_dataset_from_storage", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = [sample_real_estate_response,
                                   "saudi_real_estate_dubai_['apartment_for_rent']", '']
        response = await async_client.post("/fastapi/fetch_dataset", json=req_fetch_dataset_real_estate)
        # Assert response status and structure
        assert response.status_code == 200
        response_data = response.json()['data']
        assert "features" in response_data
        assert len(response_data["features"]) > 0
        assert "next_page_token" in response_data
        assert "delay_before_next_call" in response_data
        assert "progress" in response_data


@pytest.mark.asyncio
async def test_fetch_dataset_invalid_country(async_client, req_fetch_dataset_real_estate):
    req_fetch_dataset_real_estate["request_body"]["country_name"] = "InvalidCountry"
    response = await async_client.post("/fastapi/fetch_dataset", json=req_fetch_dataset_real_estate)
    assert response.status_code == 500
    assert "detail" in response.json()

@pytest.mark.asyncio
async def test_fetch_dataset_pai(async_client, req_fetch_dataset_pai, sample_real_estate_response):
    with patch("data_fetcher.get_census_dataset_from_storage", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = [sample_real_estate_response,
                                   "saudi_real_estate_dubai_['apartment_for_rent']", '']
        response = await async_client.post("/fastapi/fetch_dataset", json=req_fetch_dataset_pai)
        # Assert response status and structure
        assert response.status_code == 200
        response_data = response.json()['data']
        assert "features" in response_data
        assert len(response_data["features"]) > 0
        assert "next_page_token" in response_data
        assert "delay_before_next_call" in response_data
        assert "progress" in response_data

@pytest.mark.asyncio
async def test_fetch_dataset_commercial(async_client, req_fetch_dataset_commercial, sample_real_estate_response):
    with patch("data_fetcher.get_commercial_properties_dataset_from_storage", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = [sample_real_estate_response,
                                   "saudi_real_estate_dubai_['apartment_for_rent']", '']
        response = await async_client.post("/fastapi/fetch_dataset", json=req_fetch_dataset_commercial)
        # Assert response status and structure
        assert response.status_code == 200
        response_data = response.json()['data']
        assert "features" in response_data
        assert len(response_data["features"]) > 0
        assert "next_page_token" in response_data
        assert "delay_before_next_call" in response_data
        assert "progress" in response_data


@pytest.mark.asyncio
async def test_fetch_dataset_google(async_client, req_fetch_dataset_google_category_search, sample_google_category_search_response):
    with patch("data_fetcher.fetch_from_google_maps_api", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = sample_google_category_search_response
        response = await async_client.post("/fastapi/fetch_dataset", json=req_fetch_dataset_google_category_search)
        # Assert response status and structure
        assert response.status_code == 200
        response_data = response.json()['data']
        assert "features" in response_data
        assert response_data['type'] == 'FeatureCollection'
        assert len(response_data["features"]) > 0
        assert "next_page_token" in response_data
        assert "delay_before_next_call" in response_data
        assert "progress" in response_data
        assert "bknd_dataset_id" in response_data


@pytest.mark.asyncio
async def test_fetch_dataset_google_full(async_client, req_fetch_dataset_google_category_search,
                                         sample_google_category_search_response, stripe_customer,
                                         user_profile_data):
    req_fetch_dataset_google_category_search['request_body']['action'] = 'full data'
    mock_background_tasks = MagicMock()
    mock_background_tasks.add_task = MagicMock()
    with (
        patch("data_fetcher.fetch_from_google_maps_api", new_callable=AsyncMock) as mock_fetch,
        patch("data_fetcher.stripe.Customer.create_balance_transaction", new_callable=AsyncMock) as mock_strip,
        patch("data_fetcher.fetch_customer", new_callable=AsyncMock) as mock_stripe_cust,
        patch("data_fetcher.get_background_tasks", return_value=mock_background_tasks) as mock_strip,
        patch("data_fetcher.update_user_profile", new_callable=AsyncMock) as mock_strip,
        patch("backend_common.auth.db", new_callable=AsyncMock) as _mock_user_data,
    ):
        _mock_user_data.get_document.return_value = user_profile_data
        mock_fetch.return_value = sample_google_category_search_response
        mock_stripe_cust.return_value = stripe_customer
        response = await async_client.post("/fastapi/fetch_dataset", json=req_fetch_dataset_google_category_search)
        # Assert response status and structure
        assert 500 == 200  # TODO
        # response_data = response.json()['data']
        # assert "features" in response_data
        # assert response_data['type'] == 'FeatureCollection'
        # assert len(response_data["features"]) > 0
        # assert "next_page_token" in response_data
        # assert "delay_before_next_call" in response_data
        # assert "progress" in response_data
        # assert "bknd_dataset_id" in response_data
