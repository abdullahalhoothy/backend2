import pytest

@pytest.mark.asyncio
async def test_layer_collection(async_client):
    response = await async_client.get("/fastapi/layer_collection") 
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_layer_collection_empty(async_client):
    response = await async_client.get("/fastapi/layer_collection")
    response_data = response.json()
    assert len(response_data['data']) > 0 