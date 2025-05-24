import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import uuid # For checking prdcer_lyr_id format
# Need to import SqlObject from the root directory
# from sql_object import SqlObject # No longer needed as Database.fetch is not mocked here for this test
import copy 
from backend_common.constants import DEFAULT_LIMIT # To check next_page_token logic

# Import constants and helper from conftest.py
from tests.conftest import (
    USER_PROFILES_COLLECTION,
    DATASETS_COLLECTION,
    PLAN_PROGRESS_COLLECTION, # Though not used in this specific test, good to have for the module
    create_initial_db_state,
    # req_fetch_dataset_google_cafe_sample is also in conftest.py
    # user_profile_data is also in conftest.py
)

# Placeholder for actual type imports if needed for more complex scenarios
# from all_types.request_dtypes import ReqFetchDataset 
# from all_types.response_dtypes import ResFetchDataset, ResModel
# from fastapi_app import ReqModel

@pytest.mark.asyncio
async def test_fetch_dataset_sample_google_categories_success(
    async_client, 
    mock_db_instance, 
    user_profile_data, # Fixture from conftest.py
    req_fetch_dataset_google_cafe_sample # Fixture from conftest.py
):
    user_id = req_fetch_dataset_google_cafe_sample['request_body']['user_id']
    
    # 1. Define the mock dataset details to be returned by fetch_ggl_nearby
    # The bknd_dataset_id is often constructed based on query params or is a specific plan_name.
    # For 'sample' action, fetch_ggl_nearby might generate a temporary/fixed plan_id or receive one.
    # Based on the problem description, fetch_ggl_nearby's second return value is bknd_dataset_id.
    # Let's make it distinct for clarity.
    mock_bknd_dataset_id = f"google_{req_fetch_dataset_google_cafe_sample['request_body']['city_name']}_{req_fetch_dataset_google_cafe_sample['request_body']['boolean_query']}_sample"
    mock_plan_name_from_fetcher = mock_bknd_dataset_id # Often the plan_name is the same as bknd_dataset_id for google fetches
    
    mock_geojson_features = [{"type": "Feature", "properties": {"name": "Mock Cafe Dubai"}, "geometry": {"type": "Point", "coordinates": [55.2708, 25.2048]}}]
    
    # This is what fetch_ggl_nearby is mocked to return as its first element (the geojson_dataset)
    mock_geojson_data_returned_by_fetch_ggl = {
        "type": "FeatureCollection",
        "features": mock_geojson_features,
        # fetch_ggl_nearby might also include metadata, but the tuple return signature is specific
    }
    mock_next_page_token_from_fetcher = "token_cafe_dubai_next_sample"

    # 2. Prepare initial DB state
    # For a 'sample' action that calls an external fetcher, the 'datasets' collection 
    # might not need to be pre-populated with this specific data.
    # The user profile needs to exist for authentication/authorization.
    initial_user_profiles = {user_id: user_profile_data}
    db_state = create_initial_db_state(
        user_profiles=initial_user_profiles,
        datasets={} # No pre-existing dataset with mock_bknd_dataset_id needed for this 'sample' flow
    )
    mock_db_instance.set_initial_data(db_state)

    # 3. Patch data_fetcher.fetch_ggl_nearby
    with patch("data_fetcher.fetch_ggl_nearby", new_callable=AsyncMock) as mock_fetch_ggl:
        # fetch_ggl_nearby returns: (geojson_dataset, bknd_dataset_id, next_page_token, plan_name, next_plan_index)
        mock_fetch_ggl.return_value = (
            mock_geojson_data_returned_by_fetch_ggl,  # geojson_dataset (dict)
            mock_bknd_dataset_id,                     # bknd_dataset_id
            mock_next_page_token_from_fetcher,        # next_page_token
            mock_plan_name_from_fetcher,              # plan_name
            0                                         # next_plan_index (0 for sample)
        )

        # 4. Make the API call
        response = await async_client.post("/fastapi/fetch_dataset", json=req_fetch_dataset_google_cafe_sample)

    # 5. Assertions
    assert response.status_code == 200
    
    response_json = response.json()
    assert "data" in response_json
    response_data = response_json['data']

    assert response_data['features'] == mock_geojson_features
    assert response_data['bknd_dataset_id'] == mock_bknd_dataset_id
    assert response_data['next_page_token'] == mock_next_page_token_from_fetcher
    assert response_data['progress'] == 0  # As specified for sample action
    
    assert 'prdcer_lyr_id' in response_data
    assert isinstance(response_data['prdcer_lyr_id'], str)
    try:
        uuid.UUID(response_data['prdcer_lyr_id']) # Check if it's a valid UUID
    except ValueError:
        pytest.fail(f"prdcer_lyr_id '{response_data['prdcer_lyr_id']}' is not a valid UUID")
        
    assert response_data['records_count'] == len(mock_geojson_features)

    # Verify that the fetched data was saved to the 'datasets' collection
    # The endpoint is expected to store the result of fetch_ggl_nearby.
    # The structure stored in the 'datasets' collection should be the geojson_dataset 
    # returned by fetch_ggl_nearby, keyed by its bknd_dataset_id.
    saved_dataset_in_db = mock_db_instance.get_document(DATASETS_COLLECTION, mock_bknd_dataset_id)
    assert saved_dataset_in_db is not None 
    assert saved_dataset_in_db == mock_geojson_data_returned_by_fetch_ggl # Verifying the whole dict is stored
    
    # Check that fetch_ggl_nearby was called correctly
    mock_fetch_ggl.assert_called_once()
    # call_args is a tuple of positional args, call_kwargs is a dict of keyword args
    pos_args, kw_args = mock_fetch_ggl.call_args
    
    # Expected positional arguments based on fetch_ggl_nearby signature (query, city, country, action, page_token, user_id)
    assert pos_args[0] == req_fetch_dataset_google_cafe_sample['request_body']['boolean_query']
    assert pos_args[1] == req_fetch_dataset_google_cafe_sample['request_body']['city_name']
    assert pos_args[2] == req_fetch_dataset_google_cafe_sample['request_body']['country_name']
    assert pos_args[3] == req_fetch_dataset_google_cafe_sample['request_body']['action']
    assert pos_args[4] == req_fetch_dataset_google_cafe_sample['request_body']['page_token']
    assert pos_args[5] == req_fetch_dataset_google_cafe_sample['request_body']['user_id']
    
    # Expected keyword arguments
    assert kw_args.get('text_search') == req_fetch_dataset_google_cafe_sample['request_body']['text_search']
    assert kw_args.get('radius') == req_fetch_dataset_google_cafe_sample['request_body']['radius']
    assert kw_args.get('lat') == req_fetch_dataset_google_cafe_sample['request_body']['lat']
    assert kw_args.get('lng') == req_fetch_dataset_google_cafe_sample['request_body']['lng']
    assert kw_args.get('zoom_level') == req_fetch_dataset_google_cafe_sample['request_body']['zoom_level']
    # full_load is part of the request but might not be directly passed to fetch_ggl_nearby if it's handled earlier
    # For now, assuming it's not a direct kwarg to fetch_ggl_nearby unless known.
    # assert kw_args.get('full_load') == req_fetch_dataset_google_cafe_sample['request_body']['full_load']



@pytest.mark.asyncio
async def test_fetch_dataset_sample_real_estate_success(
    async_client, 
    mock_db_instance, 
    user_profile_data, 
    req_fetch_dataset_real_estate_sample, # This fixture is defined in conftest.py
    seeded_real_estate_records # This fixture from conftest.py seeds PG and yields the seeded records
):
    user_id = req_fetch_dataset_real_estate_sample['request_body']['user_id']
    req_body = req_fetch_dataset_real_estate_sample['request_body']
    city_name = req_body['city_name']
    boolean_query = req_body['boolean_query'] # This is the category, e.g., "apartment_for_rent"

    # Filter seeded_real_estate_records to match what the query in 
    # req_fetch_dataset_real_estate_sample would find.
    # The fixture seeds specific records. The request asks for "apartment_for_rent" in "Riyadh".
    matching_seeded_records = [
        r for r in seeded_real_estate_records 
        if r['category'] == boolean_query and r['city'] == city_name
    ]

    expected_geojson_features = []
    for record in matching_seeded_records:
        expected_geojson_features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [record["longitude"], record["latitude"]]},
            "properties": {
                "url": record["url"],
                "price": record["price"],
                "city": record["city"],
                "category": record["category"]
                # Latitude and longitude should NOT be in properties here as per get_real_estate_dataset_from_storage's transformation
            }
        })
    
    # Determine the expected bknd_dataset_id based on application logic
    # data_fetcher.fetch_census_realestate -> storage.get_real_estate_dataset_from_storage
    # filename = f"saudi_real_estate_{request_location.city_name.lower()}_{data_type}"
    # data_type here is an array in get_real_estate_dataset_from_storage, converted to string
    data_type_array = [boolean_query] 
    data_type_array_as_string = "_".join(sorted(data_type_array)).replace(" ", "_")
    expected_bknd_dataset_id = f"saudi_real_estate_{city_name.lower()}_{data_type_array_as_string}"
    
    # Determine expected next_page_token based on the number of matching seeded records
    # If the number of records matching the query from the seeded data is less than DEFAULT_LIMIT,
    # then next_page_token should be None (or "" which becomes None in response).
    expected_next_page_token_in_response = None if len(expected_geojson_features) < DEFAULT_LIMIT else "1" # Simplified for test

    # Firestore related setup (user profile)
    initial_user_profiles = {user_id: user_profile_data}
    # Initialize DATASETS_COLLECTION as empty for Firestore mock; data comes from PG for the main assertion
    db_state_firestore = create_initial_db_state(user_profiles=initial_user_profiles, datasets={})
    mock_db_instance.set_initial_data(db_state_firestore)

    # Mocks for services not being tested directly (check_purchase, full_load for 'sample' action)
    # Database.fetch is NOT mocked here.
    with patch("data_fetcher.check_purchase", new_callable=AsyncMock) as mock_check_purchase, \
         patch("data_fetcher.full_load", new_callable=AsyncMock) as mock_full_load:

        # For a 'sample' action, check_purchase should pass (no cost usually)
        mock_check_purchase.return_value = True 
        mock_full_load.return_value = 0 # Should not be called for sample action typically

        response = await async_client.post("/fastapi/fetch_dataset", json=req_fetch_dataset_real_estate_sample)

    assert response.status_code == 200
    response_data = response.json()['data']

    # Primary assertions: data from (real) PostgreSQL via seeded_real_estate_records
    assert response_data['features'] == expected_geojson_features
    assert response_data['records_count'] == len(expected_geojson_features)
    assert response_data['bknd_dataset_id'] == expected_bknd_dataset_id
    assert response_data['next_page_token'] == expected_next_page_token_in_response 
    assert response_data['prdcer_lyr_id'] is not None 
    assert response_data['progress'] == 0 # For sample action

    # Assertions for Firestore cache/metadata update
    # The fetch_dataset logic (specifically via fetch_census_realestate -> get_real_estate_dataset_from_storage)
    # should save the retrieved (from PG) sample to Firestore datasets collection.
    expected_firestore_metadata_next_token = "" if len(expected_geojson_features) < DEFAULT_LIMIT else "1" # Stored as "" or actual token
    
    saved_dataset_in_firestore = mock_db_instance.get_document(DATASETS_COLLECTION, expected_bknd_dataset_id)
    assert saved_dataset_in_firestore is not None
    assert saved_dataset_in_firestore['features'] == expected_geojson_features
    assert "metadata" in saved_dataset_in_firestore
    assert saved_dataset_in_firestore["metadata"]["plan_name"] == expected_bknd_dataset_id
    assert saved_dataset_in_firestore["metadata"]["next_page_token"] == expected_firestore_metadata_next_token

    # Assert that the higher-level mocks were called as expected
    mock_check_purchase.assert_called_once()
    # For a "sample" action, full_load is generally not triggered unless specific conditions are met (e.g. existing plan progress)
    # Based on the problem description, full_load is for "full data" action.
    mock_full_load.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_dataset_full_data_user_owns_dataset(
    async_client, 
    mock_db_instance, 
    user_profile_data, # Fixture from conftest.py
    req_fetch_dataset_full_data_owned, # Fixture from conftest.py
    # stripe_customer_full_data is available in conftest if needed for other tests
):
    user_id = req_fetch_dataset_full_data_owned['request_body']['user_id']
    city_name = req_fetch_dataset_full_data_owned['request_body']['city_name']
    boolean_query = req_fetch_dataset_full_data_owned['request_body']['boolean_query']
    country_name = req_fetch_dataset_full_data_owned['request_body']['country_name']

    # 1. Define a mock_plan_id 
    # This should match the logic in determine_plan_id in data_fetcher or equivalent
    mock_plan_id = f"plan_{boolean_query}_{country_name}_{city_name}"

    # 2. Modify user_profile_data for this test to reflect ownership
    owned_user_profile = copy.deepcopy(user_profile_data)
    if 'prdcer' not in owned_user_profile:
        owned_user_profile['prdcer'] = {}
    if 'prdcer_dataset' not in owned_user_profile['prdcer']:
        owned_user_profile['prdcer']['prdcer_dataset'] = {}
    owned_user_profile['prdcer']['prdcer_dataset'][mock_plan_id] = mock_plan_id # Mark as owned

    # 3. Define mock GeoJSON data for the dataset already in the DB
    mock_geojson_features_owned = [{"type": "Feature", "properties": {"name": f"Mock {boolean_query} {city_name} Owned"}, "geometry": {"type": "Point", "coordinates": [55.2708, 25.2048]}}]
    mock_existing_dataset_in_db = { # This is what's in DATASETS_COLLECTION
        "type": "FeatureCollection",
        "features": mock_geojson_features_owned,
    }
    
    initial_next_page_token_from_db_or_fetcher = f"token_{boolean_query}_{city_name}_page1"

    # 4. Prepare initial DB state
    initial_user_profiles = {user_id: owned_user_profile}
    initial_datasets = {mock_plan_id: mock_existing_dataset_in_db} 
    initial_plan_progress = {
        mock_plan_id: {
            "user_id": user_id, 
            "progress": 50, 
            "last_updated": "2023-01-01T12:00:00Z", 
            "completed_at": None,
            "next_page_token": initial_next_page_token_from_db_or_fetcher 
        }
    }
    
    db_state = create_initial_db_state(
        user_profiles=initial_user_profiles,
        datasets=initial_datasets,
        plan_progress=initial_plan_progress
    )
    mock_db_instance.set_initial_data(db_state)
    
    with patch("data_fetcher.fetch_ggl_nearby", new_callable=AsyncMock) as mock_fetch_ggl, \
         patch("data_fetcher.check_purchase", new_callable=AsyncMock) as mock_check_purchase, \
         patch("data_fetcher.full_load", new_callable=AsyncMock) as mock_full_load, \
         patch("backend_common.stripe_backend.customers.fetch_customer", new_callable=AsyncMock) as mock_stripe_fetch_customer, \
         patch("stripe.Customer.create_balance_transaction", new_callable=MagicMock) as mock_stripe_create_transaction:

        mock_fetch_ggl.return_value = (
            mock_existing_dataset_in_db,            
            mock_plan_id,                           
            initial_next_page_token_from_db_or_fetcher, 
            mock_plan_id,                           
            0                                       
        )
        mock_check_purchase.return_value = True 
        mock_full_load.return_value = initial_plan_progress[mock_plan_id]["progress"]

        response = await async_client.post("/fastapi/fetch_dataset", json=req_fetch_dataset_full_data_owned)

    assert response.status_code == 200
    response_data = response.json()['data']

    assert response_data['features'] == mock_geojson_features_owned
    assert response_data['bknd_dataset_id'] == mock_plan_id
    assert response_data['progress'] == initial_plan_progress[mock_plan_id]["progress"] 
    assert response_data['delay_before_next_call'] == 3 
    assert response_data['next_page_token'] == initial_next_page_token_from_db_or_fetcher 

    mock_fetch_ggl.assert_called_once() 
    mock_check_purchase.assert_called_once()
    
    check_purchase_args, _ = mock_check_purchase.call_args
    assert check_purchase_args[0]['user_id'] == user_id 
    assert check_purchase_args[1] == mock_plan_id    
    assert check_purchase_args[2] == user_id         
    assert isinstance(check_purchase_args[3], (int, float)) 

    mock_full_load.assert_called_once()
    full_load_args, _ = mock_full_load.call_args
    assert full_load_args[0] == req_fetch_dataset_full_data_owned['request_body']
    assert full_load_args[1] == mock_plan_id                                   
    assert isinstance(full_load_args[2], str) 
    assert full_load_args[3] == initial_next_page_token_from_db_or_fetcher
    assert full_load_args[4] == mock_existing_dataset_in_db

    mock_stripe_fetch_customer.assert_not_called()
    mock_stripe_create_transaction.assert_not_called()

    current_progress_in_db = mock_db_instance.get_document(PLAN_PROGRESS_COLLECTION, mock_plan_id)
    assert current_progress_in_db is not None
    assert current_progress_in_db['progress'] == initial_plan_progress[mock_plan_id]['progress']
    assert current_progress_in_db['next_page_token'] == initial_next_page_token_from_db_or_fetcher


@pytest.mark.asyncio
async def test_fetch_dataset_full_data_insufficient_balance(
    async_client, 
    mock_db_instance, 
    user_profile_data, # Fixture from conftest.py
    req_fetch_dataset_full_data_insufficient, # Fixture from conftest.py
    # stripe_customer_full_data is available if specific values from it were needed for the mock
):
    user_id = req_fetch_dataset_full_data_insufficient['request_body']['user_id']
    city_name = req_fetch_dataset_full_data_insufficient['request_body']['city_name']
    boolean_query = req_fetch_dataset_full_data_insufficient['request_body']['boolean_query']
    country_name = req_fetch_dataset_full_data_insufficient['request_body']['country_name']

    # 1. Define mock_plan_id
    mock_plan_id_for_insufficient = f"plan_{boolean_query}_{country_name}_{city_name}"

    # 2. Ensure user_profile_data for this test does NOT contain mock_plan_id_for_insufficient
    initial_user_profile_state = copy.deepcopy(user_profile_data)
    if 'prdcer' in initial_user_profile_state and 'prdcer_dataset' in initial_user_profile_state['prdcer']:
        initial_user_profile_state['prdcer']['prdcer_dataset'].pop(mock_plan_id_for_insufficient, None)

    # 3. Define mock GeoJSON data for the first page/sample
    mock_geojson_features_for_insufficient = [{"type": "Feature", "properties": {"name": f"Mock {boolean_query} {city_name}"}, "geometry": {"type": "Point", "coordinates": [55.2708, 25.2048]}}]
    mock_geojson_data_for_insufficient = {
        "type": "FeatureCollection",
        "features": mock_geojson_features_for_insufficient,
        # Metadata for plan_name and next_page_token is usually part of the fetch_ggl_nearby tuple,
        # not necessarily inside the GeoJSON data itself when stored.
    }
    mock_next_page_token_for_insufficient_plan = f"token_{boolean_query}_{city_name}_page1_insufficient"


    # 4. Prepare initial DB state
    initial_user_profiles = {user_id: initial_user_profile_state}
    # A sample dataset might exist from a previous "sample" action
    initial_datasets = {mock_plan_id_for_insufficient: mock_geojson_data_for_insufficient}
    # Plan progress might not exist or be at 0 if a sample was fetched but not purchased for full load
    initial_plan_progress = {
        mock_plan_id_for_insufficient: {"user_id": user_id, "progress": 0, "last_updated": None, "completed_at": None, "next_page_token": mock_next_page_token_for_insufficient_plan}
    }
    
    db_state = create_initial_db_state(
        user_profiles=initial_user_profiles,
        datasets=initial_datasets,
        plan_progress=initial_plan_progress
    )
    mock_db_instance.set_initial_data(db_state)

    # 5. Mocking Strategy
    expected_cost_cents = 1000 # Cost is $10.00

    with patch("data_fetcher.fetch_ggl_nearby", new_callable=AsyncMock) as mock_fetch_ggl, \
         patch("backend_common.stripe_backend.customers.fetch_customer", new_callable=AsyncMock) as mock_fetch_stripe_customer, \
         patch("stripe.Customer.create_balance_transaction", new_callable=MagicMock) as mock_stripe_transaction, \
         patch("data_fetcher.calculate_cost", new_callable=AsyncMock) as mock_calculate_cost, \
         patch("data_fetcher.full_load", new_callable=AsyncMock) as mock_full_load:

        mock_fetch_ggl.return_value = (
            mock_geojson_data_for_insufficient,
            mock_plan_id_for_insufficient,
            mock_next_page_token_for_insufficient_plan,
            mock_plan_id_for_insufficient,
            0 
        )
        # Simulate insufficient balance
        mock_fetch_stripe_customer.return_value = {"balance": 100, "id": "cus_mock_id_low_bal"} # $1.00 balance
        
        mock_calculate_cost.return_value = (float(expected_cost_cents / 100), float(expected_cost_cents / 100)) # Cost is $10.00

        # 6. Make the API call
        response = await async_client.post("/fastapi/fetch_dataset", json=req_fetch_dataset_full_data_insufficient)

    # 7. Assertions
    assert response.status_code == 402 # Payment Required / Specific error for insufficient funds
    response_json = response.json()
    assert response_json['detail'] == "Insufficient balance in wallet. Please top up." # Check actual error message

    # Verify mock calls
    mock_fetch_ggl.assert_called_once() # Endpoint still fetches initial data before purchase check
    mock_calculate_cost.assert_called_once()
    mock_fetch_stripe_customer.assert_called_once_with(user_id=user_id)
    
    # Crucially, these should NOT be called due to insufficient balance
    mock_stripe_transaction.assert_not_called()
    mock_full_load.assert_not_called()

    # Verify user profile in DB is unchanged (user does not gain ownership)
    unchanged_user_profile_from_db = mock_db_instance.get_document(USER_PROFILES_COLLECTION, user_id)
    assert unchanged_user_profile_from_db is not None
    # Check that the plan_id was not added to the user's owned datasets
    if 'prdcer' in unchanged_user_profile_from_db and 'prdcer_dataset' in unchanged_user_profile_from_db['prdcer']:
        assert mock_plan_id_for_insufficient not in unchanged_user_profile_from_db['prdcer']['prdcer_dataset']
    else: # If prdcer or prdcer_dataset didn't exist initially or was removed for test setup
        pass # This state is also fine, means it wasn't added

    # Verify PLAN_PROGRESS_COLLECTION for this plan is also unchanged from its initial state
    plan_progress_in_db = mock_db_instance.get_document(PLAN_PROGRESS_COLLECTION, mock_plan_id_for_insufficient)
    assert plan_progress_in_db is not None # It was set initially
    assert plan_progress_in_db['progress'] == initial_plan_progress[mock_plan_id_for_insufficient]['progress']
    assert plan_progress_in_db['last_updated'] == initial_plan_progress[mock_plan_id_for_insufficient]['last_updated']
    assert plan_progress_in_db['completed_at'] == initial_plan_progress[mock_plan_id_for_insufficient]['completed_at']
    assert plan_progress_in_db['next_page_token'] == initial_plan_progress[mock_plan_id_for_insufficient]['next_page_token']



@pytest.mark.asyncio
async def test_fetch_dataset_full_data_full_load_true_progress_100(
    async_client, 
    mock_db_instance, 
    user_profile_data, 
    req_fetch_dataset_full_load_true_completed
):
    user_id = req_fetch_dataset_full_load_true_completed['request_body']['user_id']
    # layer_id = req_fetch_dataset_full_load_true_completed['request_body']['prdcer_lyr_id'] # Not directly used for plan_id construction
    boolean_query = req_fetch_dataset_full_load_true_completed['request_body']['boolean_query']
    country_name = req_fetch_dataset_full_load_true_completed['request_body']['country_name']
    city_name = req_fetch_dataset_full_load_true_completed['request_body']['city_name']

    mock_plan_id_completed = f"plan_{boolean_query}_{country_name}_{city_name}"

    # Modify user_profile_data: Ensure the user owns this mock_plan_id_completed
    owned_user_profile_completed = copy.deepcopy(user_profile_data)
    if 'prdcer' not in owned_user_profile_completed: owned_user_profile_completed['prdcer'] = {}
    if 'prdcer_dataset' not in owned_user_profile_completed['prdcer']: owned_user_profile_completed['prdcer']['prdcer_dataset'] = {}
    owned_user_profile_completed['prdcer']['prdcer_dataset'][mock_plan_id_completed] = mock_plan_id_completed

    # Define the complete GeoJSON data that should be returned by get_full_load_geojson
    mock_complete_geojson = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"name": "Feature 1 Complete"}, "geometry": {"type": "Point", "coordinates": [1,1]}},
            {"type": "Feature", "properties": {"name": "Feature 2 Complete"}, "geometry": {"type": "Point", "coordinates": [2,2]}}
        ]
    }
    
    # Define sample GeoJSON for the initial fetch (what fetch_ggl_nearby returns)
    mock_sample_geojson_for_completed_plan = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {"name": "Sample for Completed Plan"}, "geometry": {"type": "Point", "coordinates": [0,0]}}],
        # "metadata": {"next_page_token": None, "plan_name": mock_plan_id_completed} # Optional, depends on how fetch_ggl_nearby structures its first return element
    }
    # Since progress is 100, next_page_token for the initial fetch_ggl_nearby call might be None
    mock_initial_next_page_token = None 


    # Prepare initial DB state
    from datetime import datetime, timezone # Ensure these are imported
    initial_user_profiles = {user_id: owned_user_profile_completed}
    initial_datasets = {mock_plan_id_completed: mock_sample_geojson_for_completed_plan} # Sample might be in DB
    initial_plan_progress = {
        mock_plan_id_completed: {
            "user_id": user_id,
            "progress": 100,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "next_page_token": None # Plan is complete
        }
    }
    db_state = create_initial_db_state(
        user_profiles=initial_user_profiles,
        datasets=initial_datasets,
        plan_progress=initial_plan_progress
    )
    mock_db_instance.set_initial_data(db_state)

    # Mocking Strategy
    with patch("data_fetcher.fetch_ggl_nearby", new_callable=AsyncMock) as mock_fetch_ggl, \
         patch("data_fetcher.check_purchase", new_callable=AsyncMock) as mock_check_purchase, \
         patch("data_fetcher.full_load", new_callable=AsyncMock) as mock_full_load, \
         patch("storage.get_plan", new_callable=AsyncMock) as mock_get_plan, \
         patch("storage.transform_plan_items", new_callable=AsyncMock) as mock_transform_plan_items, \
         patch("storage.get_full_load_geojson", new_callable=AsyncMock) as mock_get_full_load_geojson:

        mock_fetch_ggl.return_value = (
            mock_sample_geojson_for_completed_plan, 
            mock_plan_id_completed,
            mock_initial_next_page_token, 
            mock_plan_id_completed,
            0 # next_plan_index for initial call
        )
        # For owned and completed plan, check_purchase might still be called.
        # It should return True without needing Stripe.
        mock_check_purchase.return_value = True 
        
        # full_load is called. Since progress is 100, it should return 100.
        mock_full_load.return_value = 100 
        
        mock_plan_structure = {"items": ["item1_completed.geojson"], "some_other_plan_data": "value"}
        mock_get_plan.return_value = mock_plan_structure
        
        mock_output_filenames = ["transformed_completed_file1.geojson"]
        mock_transform_plan_items.return_value = mock_output_filenames
        
        mock_get_full_load_geojson.return_value = mock_complete_geojson

        response = await async_client.post("/fastapi/fetch_dataset", json=req_fetch_dataset_full_load_true_completed)

    # Assertions
    assert response.status_code == 200
    response_data = response.json()['data']
    
    assert response_data['progress'] == 100
    assert response_data['full_load_geojson'] == mock_complete_geojson
    # The main 'features' in response could be the sample ones, or from full_load_geojson, depending on endpoint logic.
    # Based on problem desc, if full_load_geojson is present, 'features' should be from there.
    assert response_data['features'] == mock_complete_geojson['features']
    assert response_data['bknd_dataset_id'] == mock_plan_id_completed
    assert response_data['next_page_token'] is None # Plan is complete

    # Verify mock calls
    mock_fetch_ggl.assert_called_once() # Called for initial data
    mock_check_purchase.assert_called_once() # Called to confirm ownership/status
    mock_full_load.assert_called_once() # Called, returns 100
    
    mock_get_plan.assert_called_once_with(mock_plan_id_completed)
    # The first arg to transform_plan_items is the request_body
    mock_transform_plan_items.assert_called_once_with(req_fetch_dataset_full_load_true_completed['request_body'], mock_plan_structure)
    mock_get_full_load_geojson.assert_called_once_with(mock_output_filenames)


@pytest.mark.asyncio
async def test_fetch_dataset_data_not_found_in_storage(
    async_client, 
    mock_db_instance, 
    user_profile_data, 
    req_fetch_dataset_non_existent_data # Fixture from conftest.py
):
    user_id = req_fetch_dataset_non_existent_data['request_body']['user_id']
    boolean_query = req_fetch_dataset_non_existent_data['request_body']['boolean_query']
    country_name = req_fetch_dataset_non_existent_data['request_body']['country_name']
    city_name = req_fetch_dataset_non_existent_data['request_body']['city_name']

    # 1. Define mock_plan_id
    # This plan ID will be associated with the "not found" data
    mock_plan_id_not_found = f"plan_{boolean_query}_{country_name}_{city_name}_notfound"

    # 2. Prepare initial DB state
    # Basic user profile is needed for auth. Other collections can be empty or not contain the mock_plan_id.
    initial_user_profiles = {user_id: user_profile_data}
    db_state = create_initial_db_state(
        user_profiles=initial_user_profiles,
        datasets={}, # Ensure no pre-existing dataset for this plan_id
        plan_progress={} # Ensure no pre-existing progress for this plan_id
    )
    mock_db_instance.set_initial_data(db_state)

    # 3. Mocking Strategy
    # The primary data fetching function (fetch_ggl_nearby for this query type)
    # will return values indicating no data was found.
    empty_geojson_data = {"type": "FeatureCollection", "features": []}

    with patch("data_fetcher.fetch_ggl_nearby", new_callable=AsyncMock) as mock_fetch_ggl, \
         patch("data_fetcher.check_purchase", new_callable=AsyncMock) as mock_check_purchase, \
         patch("data_fetcher.full_load", new_callable=AsyncMock) as mock_full_load:

        mock_fetch_ggl.return_value = (
            empty_geojson_data,          # geojson_dataset: empty
            mock_plan_id_not_found,      # bknd_dataset_id
            None,                        # next_page_token: None, as no data
            mock_plan_id_not_found,      # plan_name
            0                            # next_plan_index
        )
        
        # For a "sample" action, check_purchase might be called.
        # If it's for a dataset that returns no features, it should not proceed to purchase.
        # Its return value might be None or it might not be called if logic short-circuits.
        # Based on `process_fetched_data`, if `geojson_dataset` is None or features are empty,
        # it might return early. Let's assume check_purchase might not even be reached if no features.
        # However, the endpoint logic might call it regardless. For safety, we mock it.
        mock_check_purchase.return_value = None # Or True, outcome should be no purchase for sample
        
        # full_load should not be called if there's no data to load or if action is 'sample' and no data found.
        mock_full_load.return_value = 0 


        # 4. Make the API call
        response = await async_client.post("/fastapi/fetch_dataset", json=req_fetch_dataset_non_existent_data)

    # 5. Assertions
    assert response.status_code == 200 # Endpoint handles "not found" gracefully by returning empty
    
    response_data = response.json()['data']
    
    assert response_data['features'] == []
    assert response_data['records_count'] == 0
    assert response_data['bknd_dataset_id'] == mock_plan_id_not_found
    assert response_data['next_page_token'] is None
    assert response_data['progress'] == 0 # Default progress for sample or no data
    assert 'prdcer_lyr_id' in response_data # Should still generate a layer ID

    # Verify mock calls
    mock_fetch_ggl.assert_called_once()
    
    # Depending on the exact flow in `fetch_dataset` and `process_fetched_data` for empty results:
    # If data is empty, check_purchase might not be called if the logic short-circuits.
    # If it is called for 'sample' action regardless of features, then assert_called_once.
    # For now, let's assume it's called as part of the standard flow before returning.
    mock_check_purchase.assert_called_once()

    # full_load should DEFINITELY not be called if action is 'sample' and no data.
    # If action were 'full data' and data was empty, it also likely wouldn't run.
    mock_full_load.assert_not_called() # For "sample" action, full_load is not triggered from endpoint.

    # Verify that the empty dataset (if fetch_ggl_nearby returns one) is saved to the DB
    # This behavior (saving an empty dataset) depends on implementation details in data_fetcher.py
    saved_dataset = mock_db_instance.get_document(DATASETS_COLLECTION, mock_plan_id_not_found)
    assert saved_dataset is not None
    assert saved_dataset["features"] == []


@pytest.mark.asyncio
async def test_fetch_dataset_full_data_sufficient_balance_first_purchase(
    async_client, 
    mock_db_instance, 
    user_profile_data, # Fixture from conftest.py
    req_fetch_dataset_full_data_purchase, # Fixture from conftest.py
    # stripe_customer_full_data is available in conftest if needed
):
    user_id = req_fetch_dataset_full_data_purchase['request_body']['user_id']
    city_name = req_fetch_dataset_full_data_purchase['request_body']['city_name']
    boolean_query = req_fetch_dataset_full_data_purchase['request_body']['boolean_query']
    country_name = req_fetch_dataset_full_data_purchase['request_body']['country_name']

    # 1. Define mock_plan_id
    mock_plan_id_for_purchase = f"plan_{boolean_query}_{country_name}_{city_name}"

    # 2. Ensure user_profile_data for this test does NOT contain mock_plan_id_for_purchase
    current_user_profile = copy.deepcopy(user_profile_data)
    if 'prdcer' in current_user_profile and 'prdcer_dataset' in current_user_profile['prdcer']:
        current_user_profile['prdcer']['prdcer_dataset'].pop(mock_plan_id_for_purchase, None)

    # 3. Define mock GeoJSON data for the first page/sample of this new dataset
    mock_geojson_features_for_purchase = [{"type": "Feature", "properties": {"name": f"Mock {boolean_query} {city_name}"}, "geometry": {"type": "Point", "coordinates": [55.2708, 25.2048]}}]
    mock_geojson_data_for_purchase = { # This is what fetch_ggl_nearby would return as the first element
        "type": "FeatureCollection",
        "features": mock_geojson_features_for_purchase,
        # "metadata": {"next_page_token": "token_bank_dubai_next_full", "plan_name": mock_plan_id_for_purchase} # Optional
    }
    mock_next_page_token_for_new_plan_from_fetcher = f"token_{boolean_query}_{city_name}_page1_new"


    # 4. Prepare initial DB state
    initial_user_profiles = {user_id: current_user_profile}
    # For a first purchase, the dataset might already have a sample entry from a previous "sample" action
    initial_datasets = {mock_plan_id_for_purchase: mock_geojson_data_for_purchase} 
    # No progress or 0 progress for a plan not yet fully loaded by the user
    initial_plan_progress = {
        mock_plan_id_for_purchase: {"user_id": user_id, "progress": 0, "last_updated": None, "completed_at": None, "next_page_token": mock_next_page_token_for_new_plan_from_fetcher}
    }
    
    db_state = create_initial_db_state(
        user_profiles=initial_user_profiles,
        datasets=initial_datasets,
        plan_progress=initial_plan_progress # Initialize with 0 progress
    )
    mock_db_instance.set_initial_data(db_state)

    # 5. Mocking Strategy
    expected_cost_cents = 1000 # $10.00 in cents

    with patch("data_fetcher.fetch_ggl_nearby", new_callable=AsyncMock) as mock_fetch_ggl, \
         patch("backend_common.stripe_backend.customers.fetch_customer", new_callable=AsyncMock) as mock_fetch_stripe_customer, \
         patch("stripe.Customer.create_balance_transaction", new_callable=MagicMock) as mock_stripe_transaction, \
         patch("data_fetcher.calculate_cost", new_callable=AsyncMock) as mock_calculate_cost, \
         patch("data_fetcher.full_load", new_callable=AsyncMock) as mock_full_load:
         # Not mocking check_purchase itself, but its dependencies (stripe, cost calculation)

        mock_fetch_ggl.return_value = (
            mock_geojson_data_for_purchase,         # geojson_dataset
            mock_plan_id_for_purchase,              # bknd_dataset_id
            mock_next_page_token_for_new_plan_from_fetcher, # next_page_token
            mock_plan_id_for_purchase,              # plan_name
            0                                       # next_plan_index (0 for new/sample)
        )
        
        mock_stripe_customer_obj = {"balance": 50000, "id": "cus_mock_id_sufficient"} # Sufficient balance
        mock_fetch_stripe_customer.return_value = mock_stripe_customer_obj
        
        mock_calculate_cost.return_value = (float(expected_cost_cents / 100), float(expected_cost_cents / 100))
        
        mock_full_load.return_value = 0 # Initial progress for a new full load after purchase

        # 6. Make the API call
        response = await async_client.post("/fastapi/fetch_dataset", json=req_fetch_dataset_full_data_purchase)

    # 7. Assertions
    assert response.status_code == 200
    response_data = response.json()['data']

    assert response_data['bknd_dataset_id'] == mock_plan_id_for_purchase
    assert response_data['progress'] == 0 # Initial progress after purchase
    assert response_data['features'] == mock_geojson_features_for_purchase # Returns first page data

    # Verify mock calls for payment flow
    mock_fetch_stripe_customer.assert_called_once_with(user_id=user_id)
    mock_calculate_cost.assert_called_once() 
    # The description for stripe transaction might be more specific, adjust if known
    mock_stripe_transaction.assert_called_once_with(
        "cus_mock_id_sufficient", 
        amount=-expected_cost_cents, 
        currency="usd", 
        description=f"Purchase of dataset: {mock_plan_id_for_purchase}" # Or similar
    )
    
    # Verify other mocks
    mock_fetch_ggl.assert_called_once() 
    mock_full_load.assert_called_once()

    # Verify user profile update in DB (user now owns the dataset)
    updated_user_profile_from_db = mock_db_instance.get_document(USER_PROFILES_COLLECTION, user_id)
    assert updated_user_profile_from_db is not None
    assert mock_plan_id_for_purchase in updated_user_profile_from_db['prdcer']['prdcer_dataset']
    assert updated_user_profile_from_db['prdcer']['prdcer_dataset'][mock_plan_id_for_purchase] == mock_plan_id_for_purchase

    # Verify plan_progress update in DB (should be updated by the successful purchase and full_load initiation)
    plan_progress_in_db = mock_db_instance.get_document(PLAN_PROGRESS_COLLECTION, mock_plan_id_for_purchase)
    assert plan_progress_in_db is not None
    assert plan_progress_in_db['progress'] == 0 # As returned by mock_full_load
    assert plan_progress_in_db['user_id'] == user_id
    assert plan_progress_in_db['next_page_token'] == mock_next_page_token_for_new_plan_from_fetcher # Stored from fetch_ggl_nearby
    assert plan_progress_in_db['completed_at'] is None # Not yet completed
    assert plan_progress_in_db['last_updated'] is not None # Should be updated by the process



@pytest.mark.asyncio
async def test_fetch_dataset_full_data_user_owns_dataset(
    async_client, 
    mock_db_instance, 
    user_profile_data, # Fixture from conftest.py
    req_fetch_dataset_full_data_owned # Fixture from conftest.py
):
    user_id = req_fetch_dataset_full_data_owned['request_body']['user_id']
    city_name = req_fetch_dataset_full_data_owned['request_body']['city_name']
    boolean_query = req_fetch_dataset_full_data_owned['request_body']['boolean_query']

    # 1. Define a mock_plan_id based on the request
    # This logic should mirror how plan IDs are generated or identified in the application
    mock_plan_id = f"plan_{boolean_query}_{city_name}" # Simplified; actual logic might be more complex
                                                       # e.g. plan_restaurant_Dubai_full_data

    # 2. Modify user_profile_data for this test to reflect ownership
    owned_user_profile = copy.deepcopy(user_profile_data)
    if 'prdcer' not in owned_user_profile:
        owned_user_profile['prdcer'] = {}
    if 'prdcer_dataset' not in owned_user_profile['prdcer']:
        owned_user_profile['prdcer']['prdcer_dataset'] = {}
    owned_user_profile['prdcer']['prdcer_dataset'][mock_plan_id] = mock_plan_id # Mark as owned

    # 3. Define mock GeoJSON data
    mock_geojson_features_owned = [{"type": "Feature", "properties": {"name": "Mock Restaurant Dubai Owned"}, "geometry": {"type": "Point", "coordinates": [55.2708, 25.2048]}}]
    mock_geojson_data_for_owned_plan = {
        "type": "FeatureCollection",
        "features": mock_geojson_features_owned,
        # "metadata": {"next_page_token": "token_restaurant_dubai_next_full", "plan_name": mock_plan_id} # This structure is if dataset itself contains metadata
    }
    # The fetch_ggl_nearby (or equivalent) returns the dataset and tokens separately.
    initial_next_page_token = "token_restaurant_dubai_page1"


    # 4. Prepare initial DB state
    initial_user_profiles = {user_id: owned_user_profile}
    initial_datasets = {mock_plan_id: mock_geojson_data_for_owned_plan} # Dataset already exists
    initial_plan_progress = {
        mock_plan_id: {
            "user_id": user_id, # Ensure user_id is part of progress doc if needed
            "progress": 50, 
            "last_updated": "2023-01-01T12:00:00Z", # A timestamp sufficiently in the past
            "completed_at": None,
            "next_page_token": initial_next_page_token # Store the *actual* next page token for this plan
        }
    }
    
    db_state = create_initial_db_state(
        user_profiles=initial_user_profiles,
        datasets=initial_datasets,
        plan_progress=initial_plan_progress
    )
    mock_db_instance.set_initial_data(db_state)

    # 5. Patch external calls
    with patch("data_fetcher.fetch_ggl_nearby", new_callable=AsyncMock) as mock_fetch_ggl, \
         patch("data_fetcher.check_purchase", new_callable=AsyncMock) as mock_check_purchase, \
         patch("data_fetcher.full_load", new_callable=AsyncMock) as mock_full_load, \
         patch("backend_common.stripe_backend.customers.fetch_customer", new_callable=AsyncMock) as mock_fetch_stripe_customer, \
         patch("stripe.Customer.create_balance_transaction", new_callable=MagicMock) as mock_create_stripe_transaction: # MagicMock for non-async stripe lib

        # Configure mock return values
        # fetch_ggl_nearby is called to get initial details / first page if dataset is empty or for consistency.
        # For an owned dataset, this might return the first page from the existing dataset, or be called to confirm plan details.
        # Let's assume it's called and returns the first page from the existing dataset.
        mock_fetch_ggl.return_value = (
            mock_geojson_data_for_owned_plan, # Returns the existing first page data
            mock_plan_id,
            initial_next_page_token, # The token for the *next* page of the existing dataset
            mock_plan_id, # plan_name
            0 # next_plan_index (irrelevant if data already exists and progress is tracked)
        )
        
        # check_purchase: Since user owns the plan, this should pass without needing Stripe.
        # The function itself might modify request_body or return values indicating ownership.
        # For this test, we assume it's called and doesn't raise an error.
        # The actual check_purchase logic determines if user owns plan_id.
        # It will read user_profile from DB (which we've set up).
        mock_check_purchase.return_value = True # Indicating user has access / owns the plan

        # full_load: This is called since it's "full data" action and user owns it.
        # It should return the current progress.
        mock_full_load.return_value = initial_plan_progress[mock_plan_id]["progress"] # Return the current progress from DB

        # 6. Make the API call
        response = await async_client.post("/fastapi/fetch_dataset", json=req_fetch_dataset_full_data_owned)

    # 7. Assertions
    assert response.status_code == 200
    response_data = response.json()['data']

    # The returned features should be the first page of the existing dataset
    assert response_data['features'] == mock_geojson_features_owned
    assert response_data['bknd_dataset_id'] == mock_plan_id
    assert response_data['progress'] == initial_plan_progress[mock_plan_id]["progress"] # Progress from DB via full_load mock
    assert response_data['delay_before_next_call'] == 3 # As specified
    # The next_page_token in response should be the one from the plan_progress collection (or fetch_ggl_nearby if first time)
    assert response_data['next_page_token'] == initial_next_page_token 


    # Verify mock calls
    # fetch_ggl_nearby might be called to get initial info or first page.
    mock_fetch_ggl.assert_called_once() 

    # check_purchase should be called to verify ownership or payment status
    mock_check_purchase.assert_called_once()
    # Assert specific arguments for check_purchase if necessary
    # Example: mock_check_purchase.assert_called_with(ANY, mock_plan_id, user_id, ANY)
    
    # full_load should be called because user owns the dataset
    mock_full_load.assert_called_once()
    # Assert specific arguments for full_load
    # Expected: (req_body_dict, plan_id, prdcer_lyr_id_from_response, next_page_token_from_fetch_ggl, initial_geojson_data)
    # The prdcer_lyr_id is generated within the endpoint, so we can't know it beforehand easily.
    # We can capture it or use ANY from unittest.mock if needed.
    # For now, checking it was called is a good start.
    full_load_args = mock_full_load.call_args[0]
    assert full_load_args[0] == req_fetch_dataset_full_data_owned['request_body']
    assert full_load_args[1] == mock_plan_id
    assert isinstance(full_load_args[2], str) # prdcer_lyr_id
    assert full_load_args[3] == initial_next_page_token # next_page_token from fetch_ggl_nearby
    assert full_load_args[4] == mock_geojson_data_for_owned_plan # initial_geojson_data from fetch_ggl_nearby


    # Verify Stripe methods were NOT called
    mock_fetch_stripe_customer.assert_not_called()
    mock_create_stripe_transaction.assert_not_called()

    # Verify DB state for plan_progress (e.g., if last_updated changed, though full_load mock controls what's returned for progress)
    # The actual update to plan_progress happens inside the full_load background task.
    # Since we are mocking full_load itself, we won't see its DB side-effects in this specific unit test of the endpoint.
    # We are testing that the endpoint correctly *initiates* the full_load process.
    # To test the internals of full_load, separate tests for that function would be needed.
    current_progress_in_db = mock_db_instance.get_document(PLAN_PROGRESS_COLLECTION, mock_plan_id)
    assert current_progress_in_db['progress'] == initial_plan_progress[mock_plan_id]['progress'] # Should remain unchanged as full_load is mocked


# Placeholder for actual type imports if needed for more complex scenarios
# from all_types.request_dtypes import ReqFetchDataset 
# from all_types.response_dtypes import ResFetchDataset, ResModel
# from fastapi_app import ReqModel

@pytest.mark.asyncio
async def test_fetch_dataset_sample_google_categories_success_2(
    async_client, 
    mock_db_instance, 
    user_profile_data, # Fixture from conftest.py
    req_fetch_dataset_google_cafe_sample # Fixture from conftest.py
):
    user_id = req_fetch_dataset_google_cafe_sample['request_body']['user_id']
    
    # 1. Define the mock dataset details to be returned by fetch_ggl_nearby
    # The bknd_dataset_id is often constructed based on query params or is a specific plan_name.
    # For 'sample' action, fetch_ggl_nearby might generate a temporary/fixed plan_id or receive one.
    # Based on the problem description, fetch_ggl_nearby's second return value is bknd_dataset_id.
    # Let's make it distinct for clarity.
    mock_bknd_dataset_id = f"google_{req_fetch_dataset_google_cafe_sample['request_body']['city_name']}_{req_fetch_dataset_google_cafe_sample['request_body']['boolean_query']}_sample"
    mock_plan_name_from_fetcher = mock_bknd_dataset_id # Often the plan_name is the same as bknd_dataset_id for google fetches
    
    mock_geojson_features = [{"type": "Feature", "properties": {"name": "Mock Cafe Dubai"}, "geometry": {"type": "Point", "coordinates": [55.2708, 25.2048]}}]
    
    # This is what fetch_ggl_nearby is mocked to return as its first element (the geojson_dataset)
    mock_geojson_data_returned_by_fetch_ggl = {
        "type": "FeatureCollection",
        "features": mock_geojson_features,
        # fetch_ggl_nearby might also include metadata, but the tuple return signature is specific
    }
    mock_next_page_token_from_fetcher = "token_cafe_dubai_next_sample"

    # 2. Prepare initial DB state
    # For a 'sample' action that calls an external fetcher, the 'datasets' collection 
    # might not need to be pre-populated with this specific data.
    # The user profile needs to exist for authentication/authorization.
    initial_user_profiles = {user_id: user_profile_data}
    db_state = create_initial_db_state(
        user_profiles=initial_user_profiles,
        datasets={} # No pre-existing dataset with mock_bknd_dataset_id needed for this 'sample' flow
    )
    mock_db_instance.set_initial_data(db_state)

    # 3. Patch data_fetcher.fetch_ggl_nearby
    with patch("data_fetcher.fetch_ggl_nearby", new_callable=AsyncMock) as mock_fetch_ggl:
        # fetch_ggl_nearby returns: (geojson_dataset, bknd_dataset_id, next_page_token, plan_name, next_plan_index)
        mock_fetch_ggl.return_value = (
            mock_geojson_data_returned_by_fetch_ggl,  # geojson_dataset (dict)
            mock_bknd_dataset_id,                     # bknd_dataset_id
            mock_next_page_token_from_fetcher,        # next_page_token
            mock_plan_name_from_fetcher,              # plan_name
            0                                         # next_plan_index (0 for sample)
        )

        # 4. Make the API call
        response = await async_client.post("/fastapi/fetch_dataset", json=req_fetch_dataset_google_cafe_sample)

    # 5. Assertions
    assert response.status_code == 200
    
    response_json = response.json()
    assert "data" in response_json
    response_data = response_json['data']

    assert response_data['features'] == mock_geojson_features
    assert response_data['bknd_dataset_id'] == mock_bknd_dataset_id
    assert response_data['next_page_token'] == mock_next_page_token_from_fetcher
    assert response_data['progress'] == 0  # As specified for sample action
    
    assert 'prdcer_lyr_id' in response_data
    assert isinstance(response_data['prdcer_lyr_id'], str)
    try:
        uuid.UUID(response_data['prdcer_lyr_id']) # Check if it's a valid UUID
    except ValueError:
        pytest.fail(f"prdcer_lyr_id '{response_data['prdcer_lyr_id']}' is not a valid UUID")
        
    assert response_data['records_count'] == len(mock_geojson_features)

    # Verify that the fetched data was saved to the 'datasets' collection
    # The endpoint is expected to store the result of fetch_ggl_nearby.
    # The structure stored in the 'datasets' collection should be the geojson_dataset 
    # returned by fetch_ggl_nearby, keyed by its bknd_dataset_id.
    saved_dataset_in_db = mock_db_instance.get_document(DATASETS_COLLECTION, mock_bknd_dataset_id)
    assert saved_dataset_in_db is not None 
    assert saved_dataset_in_db == mock_geojson_data_returned_by_fetch_ggl # Verifying the whole dict is stored
    
    # Check that fetch_ggl_nearby was called correctly
    mock_fetch_ggl.assert_called_once()
    # call_args is a tuple of positional args, call_kwargs is a dict of keyword args
    pos_args, kw_args = mock_fetch_ggl.call_args
    
    # Expected positional arguments based on fetch_ggl_nearby signature (query, city, country, action, page_token, user_id)
    assert pos_args[0] == req_fetch_dataset_google_cafe_sample['request_body']['boolean_query']
    assert pos_args[1] == req_fetch_dataset_google_cafe_sample['request_body']['city_name']
    assert pos_args[2] == req_fetch_dataset_google_cafe_sample['request_body']['country_name']
    assert pos_args[3] == req_fetch_dataset_google_cafe_sample['request_body']['action']
    assert pos_args[4] == req_fetch_dataset_google_cafe_sample['request_body']['page_token']
    assert pos_args[5] == req_fetch_dataset_google_cafe_sample['request_body']['user_id']
    
    # Expected keyword arguments
    assert kw_args.get('text_search') == req_fetch_dataset_google_cafe_sample['request_body']['text_search']
    assert kw_args.get('radius') == req_fetch_dataset_google_cafe_sample['request_body']['radius']
    assert kw_args.get('lat') == req_fetch_dataset_google_cafe_sample['request_body']['lat']
    assert kw_args.get('lng') == req_fetch_dataset_google_cafe_sample['request_body']['lng']
    assert kw_args.get('zoom_level') == req_fetch_dataset_google_cafe_sample['request_body']['zoom_level']
    # full_load is part of the request but might not be directly passed to fetch_ggl_nearby if it's handled earlier
    # For now, assuming it's not a direct kwarg to fetch_ggl_nearby unless known.
    # assert kw_args.get('full_load') == req_fetch_dataset_google_cafe_sample['request_body']['full_load']

