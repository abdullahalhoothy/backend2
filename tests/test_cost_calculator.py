import pytest
from unittest.mock import patch, MagicMock
from cost_calculator import calculate_cost, COST_PER_1000_CALLS
from all_types.request_dtypes import ReqFetchDataset
from all_types.response_dtypes import ResCostEstimate
import math # Added for calculations in new test

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
    response_data = response.json()['data'] # Access the 'data' dictionary
    assert "cost" in response_data
    assert "api_calls" in response_data
    
    # Verify the 100x multiplication factor
    expected_cost = (response_data['api_calls'] / 1000) * COST_PER_1000_CALLS * 100
    assert response_data['cost'] == pytest.approx(expected_cost)

@pytest.mark.asyncio
@patch('cost_calculator.ensure_city_categories')
async def test_calculate_cost_directly_with_100x_multiplication(mock_ensure_categories):
    # Mock ensure_city_categories to return controlled data
    mock_ensure_categories.return_value = {"business_for_rent": 0.5}

    # Create a sample request object
    # Ensure all fields required by calculate_cost are present
    sample_req_body = {
        "country_name": "canada",
        "city_name": "montreal",
        "boolean_query": "business_for_rent",
        "search_type": "default", # or "category_search"
        # Add other fields from ReqFetchDataset if they are accessed in calculate_cost
        # For now, assuming these are the core ones for the tested logic path
        "lat": 0, "lng": 0, "user_id": "test_user", "prdcer_lyr_id": "",
        "action": "sample", "page_token": "", "text_search": "", "zoom_level": 4, "radius": 30000
    }
    mock_req = ReqFetchDataset(**sample_req_body)

    # Expected total_api_calls based on detailed calculation in thought process
    # density_score = 0.5
    # total_circles = 500
    # estimate_active_circles(0.5, 500) calculation:
    # levels = math.floor(math.log(500, 7)) + 1 = 4
    # L1: 7
    # L2: ceil(min(493, 49) * 0.5 * 0.5) = ceil(49 * 0.25) = 13. Total = 7+13=20
    # L3: ceil(min(444, 343) * 0.5 * (1/3)) = ceil(343 * 0.1666) = 58. Total = 20+58=78
    # L4: ceil(min(101, 2401) * 0.5 * 0.25) = ceil(101 * 0.125) = 13. Total = 78+13=91
    expected_api_calls = 91 
    
    # Calculate cost before 100x multiplication
    cost_before_100x = (expected_api_calls / 1000) * COST_PER_1000_CALLS
    # Expected cost after 100x multiplication
    expected_final_cost = cost_before_100x * 100

    # Call the function
    result: ResCostEstimate = await calculate_cost(mock_req)

    # Assertions
    assert result.api_calls == expected_api_calls
    assert result.cost == pytest.approx(expected_final_cost)
    
    # Verify ensure_city_categories was called correctly
    mock_ensure_categories.assert_called_once_with("canada", "montreal")
