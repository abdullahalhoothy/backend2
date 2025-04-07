import pytest

@pytest.mark.asyncio
async def test_cost_calculator(async_client, req_cost_calculator):
    response = await async_client.post("/fastapi/cost_calculator",json=req_cost_calculator)
    response_data = response.json()
    print("data returned", response_data)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_cost_calculator_querymissing(async_client, req_cost_calculator):
    req_cost_calculator["request_body"]["boolean_query"] = ""
    response = await async_client.post("/fastapi/cost_calculator",json=req_cost_calculator)
    assert response.status_code == 500

@pytest.mark.asyncio
async def test_cost_calculator_checkingfields(async_client, req_cost_calculator):
    response = await async_client.post("/fastapi/cost_calculator",json=req_cost_calculator)
    assert response.status_code == 200
    response_data = response.json()
    assert "cost" in response_data['data']
    assert "api_calls" in response_data['data']
    
    
