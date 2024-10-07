from all_types.myapi_dtypes import ReqAddPaymentMethod
from all_types.response_dtypes import ResAddPaymentMethod
from storage import load_user_profile, update_user_profile
import uuid
from typing import Dict, Any, List
from fastapi import HTTPException, status
from all_types.myapi_dtypes import ReqGetPaymentMethods
from all_types.response_dtypes import ResGetPaymentMethods, PaymentMethod
import random

async def add_payment_method(req: ReqAddPaymentMethod) -> Dict[str, Any]:
    # user_data = load_user_profile(req.user_id)
    # if not user_data:
    #     raise HTTPException(
    #         status_code=status.HTTP_404_NOT_FOUND,
    #         detail="User not found"
    #     )

    # # Generate a unique ID for the payment method
    # payment_method_id = str(uuid.uuid4())

    # # Create a new payment method object
    # new_payment_method = {
    #     "id": payment_method_id,
    #     "type": req.payment_type,
    #     "details": req.payment_details
    # }

    # # Add the new payment method to the user's profile
    # if "payment_methods" not in user_data:
    #     user_data["payment_methods"] = []
    # user_data["payment_methods"].append(new_payment_method)

    # # Update the user profile in the database
    # update_user_profile(req.user_id, user_data)

    return {"message":"thank you"}



async def get_payment_methods(req: ReqGetPaymentMethods) -> Dict[str, Any]:
    # user_data = load_user_profile(req.user_id)
    # if not user_data:
    #     raise HTTPException(
    #         status_code=status.HTTP_404_NOT_FOUND,
    #         detail="User not found"
    #     )

    # # Check if the user has any payment methods
    # user_payment_methods = user_data.get("payment_methods", [])
    # Hardcoded example payment methods
    EXAMPLE_PAYMENT_METHODS = [
        {
            "id": "pm_1234567890",
            "type": "credit_card",
            "details": {
                "last4": "4242",
                "brand": "Visa",
                "exp_month": 12,
                "exp_year": 2025
            }
        },
        {
            "id": "pm_0987654321",
            "type": "paypal",
            "details": {
                "email": "user@example.com"
            }
        },
        {
            "id": "pm_1357924680",
            "type": "bank_account",
            "details": {
                "bank_name": "Example Bank",
                "last4": "6789"
            },
            "is_default": True
        }
    ]

    # Randomly select 1-3 example payment methods
    num_examples = random.randint(1, 3)
    user_payment_methods = random.sample(EXAMPLE_PAYMENT_METHODS, num_examples)

    # Convert the payment methods to the PaymentMethod model
    payment_methods = [PaymentMethod(**method) for method in user_payment_methods]

    return ResGetPaymentMethods(payment_methods=payment_methods)