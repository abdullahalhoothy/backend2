import pytest
from unittest.mock import patch, AsyncMock
# from myapi_dtypes import ValidationResult
from all_types.myapi_dtypes import ValidationResult

@pytest.mark.asyncio
async def test_gradient_color_based_on_llm(async_client, 
                                           req_load_user_profile, 
                                           invalid_prompt_validation_response,
                                           req_GradientColorBasedOnZone):
    req_load_user_profile['request_body']['prompt'] = "prompt"
    req_load_user_profile['request_body']['layers'] = [
        {
            "banks": {
                      "id": "l1d77aec5-0c4c-4733-9297-bb6bc4f2a41a", 
                     "name": "SA-RIY-bank"
                         }
                  }
           ]
    mock_result_data = invalid_prompt_validation_response["data"]
    mock_result_data["body"] = req_GradientColorBasedOnZone["request_body"]
    mock_validation_result = ValidationResult(**mock_result_data)

    with patch("recoler_filter.PromptValidationAgent.__call__", return_value=mock_validation_result) as prompt_valid:
        response = await async_client.post("/fastapi/gradient_color_based_on_zone_llm", json=req_load_user_profile)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_gradient_color_based_on_llm_nolayers(async_client, 
                                           req_load_user_profile, 
                                           invalid_prompt_validation_response,
                                           req_GradientColorBasedOnZone,
                                           user_profile_data
                                           ):
    req_load_user_profile['request_body']['prompt'] = "prompt"
    mock_result_data = invalid_prompt_validation_response["data"]
    mock_result_data["body"] = req_GradientColorBasedOnZone["request_body"]
    mock_validation_result = ValidationResult(**mock_result_data)

    with (patch("recoler_filter.PromptValidationAgent.__call__", return_value=mock_validation_result) as prompt_valid,
          patch("backend_common.auth.db", new_callable=AsyncMock) as user_data):
        user_data.get_document.return_value = user_profile_data
        response = await async_client.post("/fastapi/gradient_color_based_on_zone_llm", json=req_load_user_profile)
        assert response.status_code == 422

@pytest.mark.asyncio
async def test_gradient_color_based_on_llm_validatedata(async_client, 
                                           req_load_user_profile, 
                                           invalid_prompt_validation_response,
                                           req_GradientColorBasedOnZone):
    req_load_user_profile['request_body']['prompt'] = "prompt"
    req_load_user_profile['request_body']['layers'] = [
        {
            "banks": {
                      "id": "l1d77aec5-0c4c-4733-9297-bb6bc4f2a41a", 
                     "name": "SA-RIY-bank"
                         }
                  }
           ]
    mock_result_data = invalid_prompt_validation_response["data"]
    mock_result_data["body"] = req_GradientColorBasedOnZone["request_body"]
    mock_validation_result = ValidationResult(**mock_result_data)

    with patch("recoler_filter.PromptValidationAgent.__call__", return_value=mock_validation_result) as prompt_valid:
        response = await async_client.post("/fastapi/gradient_color_based_on_zone_llm", json=req_load_user_profile)
        response_data = response.json()
        assert "is_valid" in response_data['data']
        assert "reason" in response_data['data']
        assert "body" in response_data['data']
        