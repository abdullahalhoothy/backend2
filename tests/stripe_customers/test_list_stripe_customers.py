from unittest.mock import AsyncMock, patch
import pytest

@pytest.mark.asynci
async def test_list_stripe_customers(async_client, res_list_stripe_customers):
   with(patch("backend_common.stripe_backend.customers.stripe.Customer.list" , return_value = res_list_stripe_customers)
         as stripe_customers_list):
      stripe_customers_list.return_value = res_list_stripe_customers
      response = await async_client.get("fastapi/list_stripe_customers")
      assert response.status_code == 200
      
        