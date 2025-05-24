# tests/integration/test_fetch_dataset.py

import httpx
import json
import logging
import asyncio
from datetime import datetime, timezone
from backend_common.database import Database
from backend_common.auth import firebase_db
import firebase_admin
from firebase_admin import auth

logger = logging.getLogger(__name__)

# Test data storage
TEST_USER_ID = None
TEST_USER_EMAIL = "dataset_test_user@test.com"
TEST_USER_PASSWORD = "DatasetTest123!"
API_BASE_URL = None


async def seed_test_user():
    """Create a test user for dataset tests"""
    global TEST_USER_ID
    
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0) as client:
        request_data = {
            "message": "Create dataset test user",
            "request_id": "test-dataset-user-001",
            "request_body": {
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD,
                "username": "Dataset Test User",
                "account_type": "individual",
                "admin_id": None,
                "show_price_on_purchase": False
            }
        }
        
        response = await client.post("/create_user_profile", json=request_data)
        
        if response.status_code == 200:
            data = response.json()
            TEST_USER_ID = data[0]["data"]["user_id"]
            logger.info(f"Created test user: {TEST_USER_ID}")
        else:
            raise Exception(f"Failed to create test user: {response.text}")


async def seed_google_maps_test_data():
    """Seed Google Maps test data"""
    # Create the test table
    create_table_query = """
        CREATE TABLE IF NOT EXISTS schema_marketplace.google_maps_test_raw (
            filename TEXT PRIMARY KEY,
            request_data TEXT,
            response_data TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """
    await Database.execute(create_table_query)
    
    # Seed test data
    test_data = [
        {
            "filename": "test_category_search_24.7136_46.6753_2000.0_inc_supermarket_exc_",
            "request_data": json.dumps({
                "lat": 24.7136,
                "lng": 46.6753,
                "radius": 2000.0,
                "includedTypes": ["supermarket"],
                "excludedTypes": []
            }),
            "response_data": json.dumps({
                "places": [
                    {
                        "id": "ChIJtest_supermarket_001",
                        "displayName": {
                            "text": "Test Supermarket Riyadh",
                            "languageCode": "en"
                        },
                        "formattedAddress": "King Fahd Road, Riyadh, Saudi Arabia",
                        "location": {
                            "latitude": 24.7136,
                            "longitude": 46.6753
                        },
                        "rating": 4.2,
                        "userRatingCount": 156,
                        "types": ["supermarket", "grocery_or_supermarket", "store"],
                        "primaryType": "supermarket",
                        "photos": [{"name": "places/test/photos/1"}]
                    }
                ]
            })
        },
        {
            "filename": "test_text_search_24.7136_46.6753_2000.0_coffee_shop",
            "request_data": json.dumps({
                "lat": 24.7136,
                "lng": 46.6753,
                "radius": 2000.0,
                "textQuery": "coffee shop"
            }),
            "response_data": json.dumps({
                "places": [
                    {
                        "id": "ChIJtest_coffee_001",
                        "displayName": {
                            "text": "Test Coffee Shop",
                            "languageCode": "en"
                        },
                        "formattedAddress": "Olaya Street, Riyadh, Saudi Arabia",
                        "location": {
                            "latitude": 24.7150,
                            "longitude": 46.6780
                        },
                        "rating": 4.5,
                        "userRatingCount": 234,
                        "types": ["cafe", "coffee_shop"],
                        "primaryType": "coffee_shop"
                    }
                ]
            })
        }
    ]
    
    for item in test_data:
        await Database.execute(
            """
            INSERT INTO schema_marketplace.google_maps_test_raw 
            (filename, request_data, response_data, created_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (filename) DO UPDATE
            SET response_data = EXCLUDED.response_data
            """,
            item["filename"],
            item["request_data"],
            item["response_data"],
            datetime.now(timezone.utc)
        )
    
    logger.info("✅ Seeded Google Maps test data")


async def seed_transformed_datasets():
    """Seed transformed dataset data that would normally be created by the API"""
    # Seed some pre-transformed data
    dataset_id = "24.7136_46.6753_2000.0_supermarket_token="
    
    await Database.execute(
        """
        INSERT INTO schema_marketplace.datasets 
        (filename, request_data, response_data, created_at)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (filename) DO NOTHING
        """,
        dataset_id,
        json.dumps({
            "lat": 24.7136,
            "lng": 46.6753,
            "radius": 2000.0,
            "boolean_query": "supermarket",
            "user_id": TEST_USER_ID
        }),
        json.dumps({
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [46.6753, 24.7136]
                    },
                    "properties": {
                        "id": "ChIJtest_supermarket_001",
                        "displayName": "Test Supermarket Riyadh",
                        "rating": 4.2,
                        "formattedAddress": "King Fahd Road, Riyadh, Saudi Arabia"
                    }
                }
            ],
            "properties": ["id", "displayName", "rating", "formattedAddress"]
        }),
        datetime.now(timezone.utc)
    )
    
    logger.info("✅ Seeded transformed datasets")


async def test_fetch_dataset_sample():
    """Test fetching dataset with sample action"""
    mock_token = f"mock_token_{TEST_USER_ID}"
    
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0) as client:
        request_data = {
            "message": "Fetch dataset sample",
            "request_id": "test-fetch-001",
            "request_body": {
                "user_id": TEST_USER_ID,
                "lat": 24.7136,
                "lng": 46.6753,
                "radius": 2000.0,
                "boolean_query": "supermarket",
                "page_token": "",
                "action": "sample",
                "search_type": ["category_search"],
                "country_name": "Saudi Arabia",
                "city_name": "Riyadh"
            }
        }
        
        response = await client.post(
            "/fetch_dataset",
            json=request_data,
            headers={"Authorization": f"Bearer {mock_token}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "features" in data["data"]
            assert len(data["data"]["features"]) > 0
            logger.info("✅ Dataset sample fetch successful")
        else:
            logger.warning(f"Dataset fetch returned: {response.status_code}")


async def test_fetch_dataset_text_search():
    """Test fetching dataset with text search"""
    mock_token = f"mock_token_{TEST_USER_ID}"
    
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0) as client:
        request_data = {
            "message": "Fetch dataset text search",
            "request_id": "test-fetch-002", 
            "request_body": {
                "user_id": TEST_USER_ID,
                "lat": 24.7136,
                "lng": 46.6753,
                "radius": 2000.0,
                "boolean_query": "@coffee shop@",
                "page_token": "",
                "action": "sample",
                "search_type": ["keyword_search"],
                "country_name": "Saudi Arabia",
                "city_name": "Riyadh"
            }
        }
        
        response = await client.post(
            "/fetch_dataset",
            json=request_data,
            headers={"Authorization": f"Bearer {mock_token}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            dataset_id = data["data"]["bknd_dataset_id"]
            assert "text_search=true" in dataset_id
            logger.info("✅ Text search dataset fetch successful")


async def test_fetch_dataset_full_data():
    """Test full data mode"""
    mock_token = f"mock_token_{TEST_USER_ID}"
    
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0) as client:
        request_data = {
            "message": "Fetch dataset full data",
            "request_id": "test-fetch-003",
            "request_body": {
                "user_id": TEST_USER_ID,
                "lat": 24.7136,
                "lng": 46.6753,
                "radius": 2000.0,
                "boolean_query": "supermarket",
                "page_token": "",
                "action": "full data",
                "search_type": ["category_search"],
                "country_name": "Saudi Arabia",
                "city_name": "Riyadh",
                "full_load": False
            }
        }
        
        response = await client.post(
            "/fetch_dataset",
            json=request_data,
            headers={"Authorization": f"Bearer {mock_token}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "next_page_token" in data["data"]
            assert "progress" in data["data"]
            logger.info("✅ Full data fetch successful")


async def cleanup_test_user():
    """Clean up test user"""
    if TEST_USER_ID:
        try:
            # Delete from Firestore
            await firebase_db.get_async_client().collection(
                "all_user_profiles"
            ).document(TEST_USER_ID).delete()
            
            await firebase_db.get_async_client().collection(
                "firebase_stripe_mappings"
            ).document(TEST_USER_ID).delete()
            
            # Delete from Firebase Auth
            auth.delete_user(TEST_USER_ID)
            
            logger.info(f"✅ Cleaned up test user: {TEST_USER_ID}")
        except Exception as e:
            logger.warning(f"Failed to cleanup test user: {e}")


async def cleanup_test_data():
    """Clean up test data from PostgreSQL"""
    # Clean up test tables
    await Database.execute("DROP TABLE IF EXISTS schema_marketplace.google_maps_test_raw")
    logger.info("✅ Cleaned up test tables")


# Main test runner function
async def run_dataset_tests(api_base_url: str):
    """Run all dataset tests"""
    global API_BASE_URL
    API_BASE_URL = api_base_url
    
    try:
        # Seed
        await seed_test_user()
        await seed_google_maps_test_data()
        await seed_transformed_datasets()
        
        # Run tests
        await test_fetch_dataset_sample()
        await test_fetch_dataset_text_search()
        await test_fetch_dataset_full_data()
        
        return True
    except Exception as e:
        logger.error(f"Dataset tests failed: {e}")
        return False
    finally:
        # Always cleanup
        await cleanup_test_user()
        await cleanup_test_data()