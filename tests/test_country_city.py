import pytest
from unittest.mock import patch

@pytest.mark.asyncio
async def test_country_city(async_client , res_country_city):

    with ( patch("data_fetcher.load_country_city" , return_value = res_country_city)):
        response = await async_client.get("/fastapi/country_city")
        assert response.status_code == 200
        
        
@pytest.mark.asyncio
async def test_country_city_existsdata(async_client , res_country_city):

    with ( patch("data_fetcher.load_country_city" , return_value = res_country_city)):
        response = await async_client.get("/fastapi/country_city")
        response_data = response.json()
        assert len(response_data['data']) > 0
