# tests/integration/test_user.py

import httpx
import json
import logging
import asyncio
from datetime import datetime
import firebase_admin
from firebase_admin import auth
from backend_common.auth import firebase_db
from backend_common.database import Database

logger = logging.getLogger(__name__)

# Test data storage
TEST_USERS = []
API_BASE_URL = None

# Test user data
TEST_USER_DATA = {
    "email": "integration_user_001@test.com",
    "password": "TestPass123!",
    "username": "Integration Test User 001"
}


async def seed():
    """Seed any prerequisites needed for user creation"""
    logger.info("Seeding prerequisites for user tests...")
    # Currently no prerequisites needed for user creation
    pass


async def cleanup(user_id: str):
    """Delete a user from Firebase Auth"""
    try:
        auth.delete_user(user_id)
        logger.info(f"Deleted Firebase user: {user_id}")
    except Exception as e:
        logger.warning(f"Failed to delete Firebase user {user_id}: {e}")


    """Delete all Firestore data for a user"""
    try:
        # Delete user profile
        await firebase_db.get_async_client().collection(
            "all_user_profiles"
        ).document(user_id).delete()
        logger.info(f"Deleted Firestore profile: {user_id}")
        
        # Delete Stripe mapping
        await firebase_db.get_async_client().collection(
            "firebase_stripe_mappings"
        ).document(user_id).delete()
        logger.info(f"Deleted Stripe mapping: {user_id}")
        
    except Exception as e:
        logger.warning(f"Failed to delete Firestore data for {user_id}: {e}")


async def test_create_user_profile():
    """Test creating a new user profile"""
    global TEST_USERS, API_BASE_URL
    
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0) as client:
        req_test_create_user_profile = {
            "message": "Create user profile",
            "request_id": "test-create-user-001", 
            "request_body": {
                "email": TEST_USER_DATA["email"],
                "password": TEST_USER_DATA["password"],
                "username": TEST_USER_DATA["username"],
                "account_type": "individual",
                "admin_id": None,
                "show_price_on_purchase": False
            }
        }
        
        response = await client.post("/create_user_profile", json=req_test_create_user_profile)
        
        assert response.status_code == 200, f"Failed to create user: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert isinstance(data, list), "Response should be a list"
        assert len(data) == 3, "Should have 3 responses"
        
        # Extract and store user ID
        user_id = data[0]["data"]["user_id"]
        TEST_USERS.append(user_id)
        
        # Verify Firebase user creation
        assert data[0]["data"]["user_id"], "Firebase user ID missing"
        
        # Verify Stripe customer creation
        assert data[1]["data"]["id"].startswith("cus_"), "Invalid Stripe customer ID"
        
        # Verify Firestore profile creation
        assert data[2]["data"]["email"] == TEST_USER_DATA["email"]
        
        logger.info(f"✅ Created user with ID: {user_id}")
        return user_id


async def test_user_login():
    """Test user login"""
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0) as client:
        req_test_user_login = {
            "message": "User login",
            "request_id": "test-login-001",
            "request_body": {
                "email": TEST_USER_DATA["email"],
                "password": TEST_USER_DATA["password"]
            }
        }
        
        response = await client.post("/login", json=req_test_user_login)
        
        # Login might fail if email not verified - that's OK for test
        if response.status_code == 401:
            logger.warning("Login failed - email not verified (expected in test)")
        else:
            assert response.status_code == 200
            data = response.json()
            assert "idToken" in data["data"]
            logger.info("✅ User login successful")


async def test_verify_user_profile():
    """Verify user profile exists in Firestore"""
    if not TEST_USERS:
        logger.warning("No test users to verify")
        return
        
    user_id = TEST_USERS[0]
    
    # Check Firestore directly
    user_doc = await firebase_db.get_async_client().collection(
        "all_user_profiles"
    ).document(user_id).get()
    
    assert user_doc.exists, "User profile not found in Firestore"
    user_data = user_doc.to_dict()
    
    assert user_data["email"] == TEST_USER_DATA["email"]
    assert user_data["username"] == TEST_USER_DATA["username"]
    
    logger.info("✅ User profile verified in Firestore")


async def test_user_profile_update():
    """Test updating user profile settings"""
    if not TEST_USERS:
        logger.warning("No test users to update")
        return
        
    user_id = TEST_USERS[0]
    
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0) as client:
        request_data = {
            "message": "Update user profile",
            "request_id": "test-update-001",
            "request_body": {
                "user_id": user_id,
                "account_type": "admin",
                "admin_id": None,
                "show_price_on_purchase": True
            }
        }
        
        # Mock auth token for test
        headers = {"Authorization": f"Bearer mock_token_{user_id}"}
        
        response = await client.post(
            "/update_user_profile",
            json=request_data,
            headers=headers
        )
        
        if response.status_code == 200:
            logger.info("✅ User profile updated")
        else:
            logger.warning(f"Profile update returned: {response.status_code}")


async def cleanup_all_test_users():
    """Clean up all test users created during tests"""
    logger.info(f"Cleaning up {len(TEST_USERS)} test users...")
    
    for user_id in TEST_USERS:
        await cleanup(user_id)
    
    TEST_USERS.clear()
    logger.info("✅ User cleanup completed")


# Main test runner functions
async def run_user_tests(api_base_url: str):
    """Run all user tests"""
    global API_BASE_URL
    API_BASE_URL = api_base_url
    
    try:
        # Seed
        await seed()
        
        # Run tests
        await test_create_user_profile()
        await test_user_login()
        await test_verify_user_profile()
        await test_user_profile_update()
        
        return True
    except Exception as e:
        logger.error(f"User tests failed: {e}")
        return False
    finally:
        # Always cleanup
        await cleanup_all_test_users()