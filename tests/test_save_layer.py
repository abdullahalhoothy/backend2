import logging
import pytest
import copy # For deep copying initial data if necessary

# Assuming MockFirestoreDB is in tests.mock_db and conftest.py sets up async_client and mock_db_instance
# req_save_layer, user_profile_data, req_save_layer_duplicate are fixtures from conftest.py
from tests.conftest import (
    USER_PROFILES_COLLECTION,
    DATASET_LAYER_MATCHING_COLLECTION,
    USER_LAYER_MATCHING_COLLECTION,
    create_initial_db_state
)

@pytest.mark.asyncio
async def test_save_layer(async_client, mock_db_instance, req_save_layer, user_profile_data):
    user_id = req_save_layer['request_body']['user_id']
    layer_id = req_save_layer['request_body']['prdcer_lyr_id']

    # Ensure the layer to be added is NOT in the initial user_profile_data for this test
    initial_profile_data_for_test = copy.deepcopy(user_profile_data)
    if layer_id in initial_profile_data_for_test['prdcer']['prdcer_lyrs']:
        del initial_profile_data_for_test['prdcer']['prdcer_lyrs'][layer_id]

    initial_db_state = create_initial_db_state(
        user_profiles={user_id: initial_profile_data_for_test}
        # DATASET_LAYER_MATCHING_COLLECTION and USER_LAYER_MATCHING_COLLECTION will default to empty
    )
    mock_db_instance.set_initial_data(initial_db_state)

    response = await async_client.post("/fastapi/save_layer", json=req_save_layer)

    assert response.status_code == 200
    
    # Verify response body structure (optional, but good practice)
    response_json = response.json()
    assert "message" in response_json
    assert response_json["message"] == "Layer saved successfully"
    assert "layer_id" in response_json
    assert response_json["layer_id"] == layer_id

    updated_profile = mock_db_instance.get_document(USER_PROFILES_COLLECTION, user_id)
    assert updated_profile is not None
    assert layer_id in updated_profile['prdcer']['prdcer_lyrs']
    
    saved_layer_data = updated_profile['prdcer']['prdcer_lyrs'][layer_id]
    request_layer_data = req_save_layer['request_body']
    
    assert saved_layer_data['prdcer_layer_name'] == request_layer_data['prdcer_layer_name']
    assert saved_layer_data['prdcer_lyr_id'] == request_layer_data['prdcer_lyr_id']
    assert saved_layer_data['bknd_dataset_id'] == request_layer_data['bknd_dataset_id']
    assert saved_layer_data['points_color'] == request_layer_data['points_color']
    assert saved_layer_data['layer_legend'] == request_layer_data['layer_legend']
    assert saved_layer_data['layer_description'] == request_layer_data['layer_description']
    assert saved_layer_data['city_name'] == request_layer_data['city_name']
    # user_id is not part of the layer data itself in the profile

    # Check if dataset_layer_matching and user_layer_matching were updated (basic check)
    # More detailed checks would require knowing how these collections are structured
    dataset_matching = mock_db_instance.get_collection(DATASET_LAYER_MATCHING_COLLECTION)
    # Example: assert bknd_dataset_id in dataset_matching, if that's expected
    user_matching = mock_db_instance.get_collection(USER_LAYER_MATCHING_COLLECTION)
    # Example: assert layer_id in user_matching, if that's expected


@pytest.mark.asyncio
async def test_save_layer_fail(async_client, mock_db_instance, req_save_layer_duplicate, user_profile_data):
    user_id = req_save_layer_duplicate['request_body']['user_id']
    layer_id_to_duplicate = req_save_layer_duplicate['request_body']['prdcer_lyr_id']

    # Ensure the layer to be "duplicated" IS ALREADY in the initial user_profile_data
    # The user_profile_data fixture already contains 'le2014eaa-2330-4765-93b6-1800edd4979f'
    # which matches req_save_layer_duplicate's 'prdcer_lyr_id'.
    initial_profile_with_duplicate_for_test = copy.deepcopy(user_profile_data)
    assert layer_id_to_duplicate in initial_profile_with_duplicate_for_test['prdcer']['prdcer_lyrs']

    initial_db_state = create_initial_db_state(
        user_profiles={user_id: initial_profile_with_duplicate_for_test}
    )
    mock_db_instance.set_initial_data(initial_db_state)

    response = await async_client.post("/fastapi/save_layer", json=req_save_layer_duplicate)

    assert response.status_code == 400
    
    # Verify response body structure for error (optional)
    response_json = response.json()
    assert "detail" in response_json # FastAPI default error response
    # Example: assert response_json["detail"] == "Layer with this ID already exists." 
    # This depends on the actual error message from the endpoint.

    profile_after_fail = mock_db_instance.get_document(USER_PROFILES_COLLECTION, user_id)
    assert profile_after_fail is not None
    
    # Assert that the prdcer_lyrs section is identical to the one before the call
    # This means the duplicate layer was not added again, and other layers were not affected.
    assert profile_after_fail['prdcer']['prdcer_lyrs'] == initial_profile_with_duplicate['prdcer']['prdcer_lyrs']

    # Also, ensure other parts of the profile didn't change unexpectedly
    for key in initial_profile_with_duplicate:
        if key != 'prdcer': # 'prdcer' is checked above via 'prdcer_lyrs'
             assert profile_after_fail.get(key) == initial_profile_with_duplicate.get(key)
        elif 'prdcer_lyrs' in profile_after_fail.get('prdcer', {}) and 'prdcer_lyrs' in initial_profile_with_duplicate.get('prdcer', {}):
            # For 'prdcer', specifically compare 'prdcer_lyrs' as other sub-keys might exist and change (e.g. progress fields)
             assert profile_after_fail['prdcer']['prdcer_lyrs'] == initial_profile_with_duplicate['prdcer']['prdcer_lyrs']

    # Check that dataset_layer_matching and user_layer_matching were not unexpectedly changed
    # These checks depend on the expected behavior in a failure case.
    # For simplicity, we can check if they are still empty or match their initial state.
    dataset_matching_after_fail = mock_db_instance.get_collection(DATASET_LAYER_MATCHING_COLLECTION)
    assert dataset_matching_after_fail == initial_db_state[DATASET_LAYER_MATCHING_COLLECTION]
    
    user_matching_after_fail = mock_db_instance.get_collection(USER_LAYER_MATCHING_COLLECTION)
    assert user_matching_after_fail == initial_db_state[USER_LAYER_MATCHING_COLLECTION]
