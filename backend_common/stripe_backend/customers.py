from datetime import datetime
from fastapi import HTTPException, status
from backend_common.dtypes.stripe_dtypes import (
    CustomerReq,
    CustomerRes,
)
from all_types.internal_types import UserId
import stripe
from backend_common.database import Database
import json
from backend_common.auth import (
    get_user_email_and_username,
    get_stripe_customer_id,
    save_customer_mapping,
)


# customer functions
async def create_stripe_customer(req: str) -> dict:
    user_id = req
    # Check if customer mapping already exists
    email, username = await get_user_email_and_username(user_id)

    # Create a new customer in Stripe
    metadata_dict = {"user_id": user_id}

    customer = stripe.Customer.create(
        name=username,
        email=email,
        description="",
        phone="",
        address="",
        metadata=metadata_dict,
        balance=0,
    )

    # Save the mapping in Firestore
    await save_customer_mapping(user_id, customer.id)

    customer_json = dict(customer)
    customer_json["user_id"] = user_id

    return customer_json


async def fetch_customer(req=None, user_id=None) -> dict:
    user_id = user_id or req.user_id
    customer_id = await get_stripe_customer_id(user_id)
    customer = stripe.Customer.retrieve(customer_id)

    customer_json = dict(customer)
    return customer_json


async def update_customer(req: CustomerReq) -> dict:
    customer_id = await get_stripe_customer_id(
        req.user_id
    )  # This will raise 404 if not found
    stripe_customer = stripe.Customer.modify(
        customer_id,
        name=req.name,
        email=req.email,
        description=req.description,
        phone=req.phone,
        address=req.address.model_dump(),
        metadata=req.metadata,
    )
    return dict(stripe_customer)


async def list_customers() -> list[dict]:
    all_customers = stripe.Customer.list()
    return [customer for customer in all_customers["data"]]


async def get_customer_spending(req: UserId) -> dict:
    """Retrieve all spending for a specified customer."""
    user_id = req.user_id
    customer_id = await get_stripe_customer_id(user_id)
    
    # Get charges for this customer
    charges = stripe.Charge.list(customer=customer_id)
    
    # Get invoices for this customer (optional but provides more detail)
    invoices = stripe.Invoice.list(customer=customer_id)
    
    # Compile spending data
    spending_data = {
        "charges": [dict(charge) for charge in charges.data],
        "invoices": [dict(invoice) for invoice in invoices.data],
        "total_amount": sum(charge.amount for charge in charges.data if charge.paid),
        "currency": charges.data[0].currency if charges.data else None
    }
    
    return spending_data
