from fastapi import HTTPException
from all_types.stripe_dtypes import (
    PaymentMethodReq,
    PaymentMethodRes,
    PaymentMethodUpdateReq,
)
import stripe
from backend_common.database import Database
import json
from backend_common.stripe_backend.customers import fetch_customer

# Payment methods
async def create_payment_method(
    user_id: str, req: PaymentMethodReq
) -> PaymentMethodRes:
    customer = await fetch_customer(user_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    print(req)
    # Create a payment method in Stripe
    payment_method = stripe.PaymentMethod.create(
        type=req.type,
        card=req.card.dict(),  # Card details if applicable
        billing_details=req.billing_details.dict(),
    )

    # Attach the payment method to the customer
    stripe.PaymentMethod.attach(payment_method.id, customer=customer["customer_id"])

    # Optionally store the payment method in the database for future use
    query = """
    INSERT INTO stripe_payment_methods (payment_method_id, user_id, customer_id, type, billing_details)
    VALUES ($1, $2, $3, $4, $5) RETURNING *
    """
    payment_method_record = await Database.execute(
        query,
        payment_method.id,
        user_id,
        customer["customer_id"],
        req.type,
        json.dumps(req.billing_details),
    )

    return PaymentMethodRes(
        id=payment_method.id,
        type=payment_method.type,
        customer_id=customer["customer_id"],
        billing_details=req.billing_details,
    )


async def update_payment_method(
    payment_method_id: str, req: PaymentMethodUpdateReq
) -> PaymentMethodRes:
    # Update the payment method in Stripe
    payment_method = stripe.PaymentMethod.modify(
        payment_method_id,
        billing_details=req.billing_details.dict() if req.billing_details else None,
    )

    # Update the record in the database (Optional)
    query = """
    UPDATE stripe_payment_methods
    SET billing_details = $1
    WHERE payment_method_id = $2
    RETURNING *
    """
    payment_method_record = await Database.execute(
        query, json.dumps(req.billing_details), payment_method_id
    )

    return PaymentMethodRes(
        id=payment_method["id"],
        type=payment_method["type"],
        customer_id=payment_method["customer"],
        billing_details=req.billing_details,
    )


async def delete_payment_method(payment_method_id: str) -> dict:
    # Detach the payment method from Stripe (Stripe doesn't delete but detaches it)
    payment_method = stripe.PaymentMethod.detach(payment_method_id)

    # Remove the payment method from the database (Optional)
    query = "DELETE FROM stripe_payment_methods WHERE payment_method_id = $1"
    await Database.execute(query, payment_method_id)

    return {"message": "Payment method deleted", "payment_method_id": payment_method_id}


async def set_default_payment_method(user_id: str, payment_method_id: str) -> dict:
    customer = await fetch_customer(user_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Update the default payment method for the customer in Stripe
    stripe.Customer.modify(
        customer["customer_id"],
        invoice_settings={"default_payment_method": payment_method_id},
    )

    return {
        "message": "Default payment method set",
        "payment_method_id": payment_method_id,
    }


async def list_payment_methods(user_id: str) -> dict:
    customer = await fetch_customer(user_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Fetch payment methods from Stripe
    payment_methods = stripe.PaymentMethod.list(
        customer=customer["customer_id"],
        type="card",  # You can also specify other types like 'bank_account', etc.
    )

    return {"payment_methods": payment_methods["data"]}


# for testing, create the payment source
async def testing_create_card_payment_source(
    user_id: str, source: str = "tok_visa"
) -> dict:
    customer = await fetch_customer(user_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Create a payment method in Stripe
    payment_method = stripe.Customer.create_source(customer.id, source=str(source))

    return {"message": "Payment method created"}


async def attach_payment_method_to_customer(
    user_id: str, payment_method_id: str
) -> dict:
    customer = await fetch_customer(user_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Attach the payment method to the customer
    stripe.PaymentMethod.attach(payment_method_id, customer=customer["customer_id"])

    return {
        "message": "Payment method attached",
        "payment_method_id": payment_method_id,
    }

