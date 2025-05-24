import pytest

@pytest.mark.asyncio
async def test_nearby_categories(async_client):
    response = await async_client.get("/fastapi/nearby_categories")  
    assert response.status_code == 200  
    response_data = response.json()
    assert "data" in response_data  # Adjust based on response model
  
@pytest.mark.asyncio
async def test_nearby_categories_checking_notempty(async_client):
    response = await async_client.get("/fastapi/nearby_categories")  
    response_data = response.json()
    assert len(response_data['data']) > 0


