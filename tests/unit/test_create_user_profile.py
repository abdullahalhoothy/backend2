import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.mark.asyncio
async def test_save_layer(async_client, req_create_user_profile, firebase_sign_in, stripe_customer_full_data):
    mock_background_tasks = MagicMock()
    mock_background_tasks.uid = 'sadsad'
    mock_background_tasks.id = 'sadsad'
    with (
        patch("backend_common.auth.auth.create_user", return_value=mock_background_tasks) as mock_firebase_user,
        patch("backend_common.auth.make_firebase_api_request", new_callable=AsyncMock) as mock_firebase_user_signin,
        patch("backend_common.stripe_backend.customers.stripe.Customer.create", return_value=mock_background_tasks) as mock_stripe_customer,
        patch("backend_common.stripe_backend.customers.save_customer_mapping", new_callable=AsyncMock) as mock_stripe_customer,
        patch("backend_common.stripe_backend.customers.get_user_email_and_username", new_callable=AsyncMock) as mock_user,
        patch("fastapi_app.create_user_profile", new_callable=AsyncMock) as mock_user_profile,

    ):
        mock_firebase_user_signin.return_value = firebase_sign_in
        mock_stripe_customer.return_value = stripe_customer_full_data
        mock_user.return_value = ['string', 'string']
        mock_user_profile.return_value = {}
        response = await async_client.post("/fastapi/create_user_profile", json=req_create_user_profile)
        assert response.status_code == 200
