from fastapi.testclient import TestClient
import pytest
from fastapi_app import get_fastapi_app
from unittest.mock import  MagicMock


tested_email = f"foulane@alfoulany.com" 

mock_req_data = {
    "message": "Request from frontend",
    "request_info": {},
    "request_body": {
        "email": tested_email,
        "password": "falafel",
        "username": "Foulane"
    }
}


expected_response = [
    {
        "data": {
            "user_id": "aUwY6HuCN4QnantqBnhlY2Wwbdl2",
            "message": "User profile created successfully"
        },
        "message": "Request received.",
        "request_id": "req-770fb4b8-9c2d-4345-85b6-3bed74541bbb"
    },
    {
        "data": {
            "id":"cus_RvUN60KGJIyLmb",
            "object": "customer",
            "address": None,
            "balance": 0,
            "created": 1741740215,
            "currency": None,
            "default_source": None,
            "delinquent": False,
            "description": None,
            "discount": None,
            "email": tested_email,
            "invoice_prefix": "2A10BCE5",
            "invoice_settings": {
                "custom_fields": None,
                "default_payment_method": None,
                "footer": None,
                "rendering_options": None
            },
            "livemode": False,
            "metadata": {
                "user_id": "aUwY6HuCN4QnantqBnhlY2Wwbdl2"
            },
            "name": "Foulane",
            "next_invoice_sequence": 1,
            "phone": None,
            "preferred_locales": [],
            "shipping": None,
            "tax_exempt": "none",
            "test_clock": None,
            "user_id": "aUwY6HuCN4QnantqBnhlY2Wwbdl2"
        },
        "message": "Request received.",
        "request_id": "req-0efc2242-043d-473a-8da1-fa533ee78037"
    },
    {
        "data": {
            "user_id": "aUwY6HuCN4QnantqBnhlY2Wwbdl2",
            "email": tested_email,
            "username": "Foulane",
            "account_type": "admin",
            "admin_id": None,
            "settings": {
                "show_price_on_purchase": False
            },
            "prdcer": {
                "prdcer_dataset": {
                    "dataset_plan": "",
                    "progress": 25,
                    "dataset_next_refresh_date": "2025-06-12T00:43:36.041862",
                    "auto_refresh": True
                },
                "prdcer_lyrs": {},
                "prdcer_ctlgs": {},
                "draft_ctlgs": {}
            }
        },
        "message": "Request received.",
        "request_id": "req-7dbc3d52-0f87-47ae-94ad-71f5ed2c8a04"
    }
]

@pytest.fixture
def client():
    app = get_fastapi_app()
    return TestClient(app)

def test_create_user_profile(client, mocker):
    request_id = "req-770fb4b8-9c2d-4345-85b6-3bed74541bbb"
      # Mock the Firebase admin functions
    mock_create_user = mocker.patch(
        "firebase_admin.auth.create_user", 
        return_value=MagicMock(uid="aUwY6HuCN4QnantqBnhlY2Wwbdl2")
    )
    
    mock_get_user = mocker.patch(
        "firebase_admin.auth.get_user", 
        return_value=MagicMock(uid="aUwY6HuCN4QnantqBnhlY2Wwbdl2", email="test@example.com")
    )
    
    mock_firebase_api_request = mocker.patch(
        "backend_common.auth.make_firebase_api_request", 
        side_effect=[{"idToken": "mock_id_token"}, {}]
    )
    
    mock_request_handling = mocker.patch(
        "backend_common.request_processor.request_handling", 
        return_value=[{
            "data": {
                "user_id": "aUwY6HuCN4QnantqBnhlY2Wwbdl2", 
                "message": "User profile created successfully"
            },
            "message": "Request received.",
            "request_id": request_id
        }]
    )
    response = client.post("/fastapi/create_user_profile", json=mock_req_data)
    print(response)

    assert response.status_code == 200 , f"Unexpected response: {response.txt}"



def test_create_user_profile_email_taken(client, mocker):
    fixed_uuid = "req-770fb4b8-9c2d-4345-85b6-3bed74541bbb"
    
    # Mock the Firebase create_user function to simulate the "Email already taken" error
    mock_create_user = mocker.patch(
        "firebase_admin.auth.create_user", 
        side_effect=Exception("Email already taken")  # Simulate the error when email is already taken
    )
    
    # Mock other dependencies as needed
    mock_get_user = mocker.patch(
        "firebase_admin.auth.get_user", 
        return_value=MagicMock(uid="aUwY6HuCN4QnantqBnhlY2Wwbdl2", email="test@example.com")
    )
    
    mock_firebase_api_request = mocker.patch(
        "backend_common.auth.make_firebase_api_request", 
        side_effect=[{"idToken": "mock_id_token"}, {}]
    )
    
    mock_request_handling = mocker.patch(
        "backend_common.request_processor.request_handling", 
        return_value=[{
            "data": {
                "user_id": "aUwY6HuCN4QnantqBnhlY2Wwbdl2", 
                "message": "User profile created successfully"
            },
            "message": "Request received.",
            "request_id": fixed_uuid
        }]
    )

    # Send the request to the endpoint
    response = client.post("/fastapi/create_user_profile", json=mock_req_data)

    # Assert the response status code and message
    assert response.status_code == 400, f"Unexpected response: {response.text}"
    # assert response.json() == {"detail": "Email already taken"}