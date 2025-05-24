from unittest.mock import AsyncMock,patch
import pytest
from fastapi import status, HTTPException
@pytest.mark.asyncio
async def test_fetch_stripe_customer(async_client , res_list_stripe_customers , req_load_user_profile):
    with (patch("backend_common.auth.db" , new_callable=AsyncMock) as stripe_id,
          patch("backend_common.stripe_backend.customers.stripe.Customer.retrieve" , return_value= res_list_stripe_customers )
          ):
        stripe_id.get_document.return_value = {
                                    "stripe_customer_id": "id"} 
        
        response = await async_client.post("/fastapi/fetch_stripe_customer" , json=req_load_user_profile)
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_fetch_stripe_customer_nouserfound(async_client , res_list_stripe_customers , req_load_user_profile):
    with (patch("backend_common.auth.db" , new_callable=AsyncMock) as stripe_id,
          patch("backend_common.stripe_backend.customers.stripe.Customer.retrieve" , return_value= res_list_stripe_customers )
          ):
        stripe_id.get_document.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Stripe customer not found for this user",
        )       
        
        response = await async_client.post("/fastapi/fetch_stripe_customer" , json=req_load_user_profile)
        assert response.status_code == 404