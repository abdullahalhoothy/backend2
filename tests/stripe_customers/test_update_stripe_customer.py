import pytest
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException, status
@pytest.mark.asyncio
async def test_update_stripe_customer(async_client, req_update_stripe_customer):

    with(patch("backend_common.auth.db" , new_callable=AsyncMock)as stripe_id
          ,patch("backend_common.stripe_backend.customers.stripe.Customer.modify") as update_data_def
          ):
       stripe_id.get_document.return_value = {
              "stripe_customer_id": "id"}                                              
       response = await async_client.put("/fastapi/update_stripe_customer", json=req_update_stripe_customer)
       assert response.status_code == 200

@pytest.mark.asyncio
async def test_update_stripe_customer_fail(async_client, req_update_stripe_customer):

    with(patch("backend_common.auth.db" , new_callable=AsyncMock)as stripe_id
          ,patch("backend_common.stripe_backend.customers.stripe.Customer.modify") as update_data_def
          ):
       stripe_id.get_document.side_effect = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stripe customer not found for this user",
        )                                          
       response = await async_client.put("/fastapi/update_stripe_customer", json=req_update_stripe_customer)
       assert response.status_code == 404
       
