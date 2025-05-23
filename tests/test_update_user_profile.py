import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import copy
from tests.conftest import (
    USER_PROFILES_COLLECTION,
    create_initial_db_state
)

@pytest.mark.asyncio
async def test_update_user_profile(async_client, mock_db_instance, req_load_user_profile, user_profile_data):
    # Use a deep copy of the user_profile_data fixture for initial state
    initial_profile_for_test = copy.deepcopy(user_profile_data)
    user_id = initial_profile_for_test['user_id']

    # Set initial state in MockFirestoreDB using the helper
    initial_db_state = create_initial_db_state(
        user_profiles={user_id: initial_profile_for_test}
    )
    mock_db_instance.set_initial_data(initial_db_state)

    # Prepare the request body for the update operation
    # Ensure the user_id in the request matches the one in user_profile_data
    update_request_payload = copy.deepcopy(req_load_user_profile)
    update_request_payload['request_body']['user_id'] = user_id
    
    # Define the changes to be made
    updated_account_type = "member" # Original is 'admin'
    updated_admin_id = "new_admin_id_123" # Original is None
    updated_show_price = False # Original is True
    
    update_request_payload['request_body']['account_type'] = updated_account_type
    update_request_payload['request_body']['admin_id'] = updated_admin_id
    # Assuming settings are updated as a whole dictionary if provided
    update_request_payload['request_body']['settings'] = {'show_price_on_purchase': updated_show_price}
    # Add a prdcer field to update, if the endpoint is expected to handle it
    updated_prdcer_dataset_plan = "plan_updated_value"
    update_request_payload['request_body']['prdcer'] = {
        "prdcer_dataset": {
            "dataset_plan": updated_prdcer_dataset_plan
        }
    }


    # Mock for background tasks if still necessary (likely if endpoint uses it directly)
    mock_bg_tasks = MagicMock()
    mock_bg_tasks.add_task = MagicMock()
    
    # The patch for backend_common.auth.db is handled by mock_db_instance via conftest.py
    # We only need to patch get_background_tasks if the endpoint itself uses it.
    with patch("backend_common.auth.get_background_tasks", return_value=mock_bg_tasks):
        response = await async_client.post("/fastapi/update_user_profile", json=update_request_payload)

    assert response.status_code == 200
    response_data = response.json().get('data', {})
    
    # Assertions for the response from the endpoint
    assert response_data['user_id'] == user_id
    assert response_data['account_type'] == updated_account_type
    assert response_data['admin_id'] == updated_admin_id
    assert response_data.get('settings', {}).get('show_price_on_purchase') == updated_show_price
    assert response_data.get('prdcer', {}).get('prdcer_dataset', {}).get('dataset_plan') == updated_prdcer_dataset_plan

    # Assertions for the state in MockFirestoreDB
    # This relies on the assumption that the endpoint's call to update the DB
    # is correctly routed to mock_db_instance.update_document by the patches in conftest.py.
    updated_profile_from_db = mock_db_instance.get_document(USER_PROFILES_COLLECTION, user_id)
    assert updated_profile_from_db is not None
    assert updated_profile_from_db['user_id'] == user_id
    assert updated_profile_from_db['account_type'] == updated_account_type
    assert updated_profile_from_db['admin_id'] == updated_admin_id
    assert updated_profile_from_db.get('settings', {}).get('show_price_on_purchase') == updated_show_price
    assert updated_profile_from_db.get('prdcer', {}).get('prdcer_dataset', {}).get('dataset_plan') == updated_prdcer_dataset_plan

    # Verify that fields not included in the update request remain unchanged
    assert updated_profile_from_db['email'] == initial_profile_for_test['email']
    assert updated_profile_from_db['username'] == initial_profile_for_test['username']
    # Check a field within prdcer that wasn't part of this specific update, but was in initial prdcer data
    if 'prdcer_lyrs' in initial_profile_for_test.get('prdcer', {}):
         assert updated_profile_from_db.get('prdcer', {}).get('prdcer_lyrs') == initial_profile_for_test['prdcer']['prdcer_lyrs']
