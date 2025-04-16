import pytest

async def test_fetch_gradient_colors(async_client):
    response = await async_client.get("/fastapi/fetch_gradient_colors")
    assert response.status_code == 200

async def test_fetch_gradient_colorsdata(async_client):
    response = await async_client.get("/fastapi/fetch_gradient_colors")
    response_data = response.json()
    assert len(response_data['data']) == 3
