from datetime import datetime
from fastapi import HTTPException
from all_types.stripe_dtypes import (
    CustomerReq,
    CustomerRes,
)
import stripe
from backend_common.database import Database
import json
from backend_common.auth import get_user_email_and_username

# customer functions
async def create_customer(req: CustomerReq) -> CustomerRes:
    # using user_id get from firebase user_email, user_name
    email, username = get_user_email_and_username(req.user_id)

    # Create a new customer in Stripe
    customer = stripe.Customer.create(
        name=username,
        email=email,
        description=req.description,
        phone=req.phone,
        address=req.address.model_dump(),
        metadata=req.metadata,
    )
    
    # Save the customer in the database
    query = "INSERT INTO stripe_customers (user_id, customer_id) VALUES ($1, $2) RETURNING *"
    customer_json = dict(customer)


    customer = await Database.execute(
        query,
        req.user_id,
        customer.id
    )

    customer_json["user_id"] = req.user_id

    return CustomerRes(**customer_json)


async def fetch_customer(user_id) -> CustomerRes:
    sql = "SELECT * FROM stripe_customers WHERE user_id = $1"
    customer = await Database.fetchrow(sql, user_id)
    if not customer:
        return None
    customer_dict = dict(customer)

    # Modify the dictionary
    customer_dict["metadata"] = json.loads(customer_dict["metadata"])
    customer_dict["address"] = json.loads(customer_dict["address"])
    customer_dict["created"] = int(customer_dict["created"].timestamp())
    customer_dict["preferred_locales"] = json.loads(customer_dict["preferred_locales"])
    customer_dict["id"] = customer_dict["customer_id"]
    return CustomerRes(**customer_dict)


async def update_customer(req: CustomerReq) -> CustomerRes:
    stripe_customer = stripe.Customer.modify(
        req.user_id,
        name=req.name,
        email=req.email,
        description=req.description,
        phone=req.phone,
        address=req.address.model_dump(),
        metadata=req.metadata,
    )

    query = "UPDATE stripe_customers SET name = $1, email = $2, description = $3, phone = $4, address = $5, metadata = $6 WHERE user_id = $7 RETURNING *"

    customer = await Database.execute(
        query,
        req.name,
        req.email,
        req.description,
        req.phone,
        req.address.dict(),
        req.metadata.dict(),
        req.user_id,
    )

    return CustomerRes(**customer)


async def delete_customer(req) -> dict:
    user_id = req.user_id
    # get the customer from the database
    # delete the customer from stripe
    # delete the customer from the database

    customer = await fetch_customer(user_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    stripe.Customer.delete(customer.id)
    try:
        query = "DELETE FROM stripe_customers WHERE customer_id = $1"

        await Database.execute(query, user_id)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=404, detail="Customer")
    return "Customer deleted"


async def list_customers() -> list[CustomerRes]:
    all_customers = stripe.Customer.list()

    return [CustomerRes(**customer) for customer in all_customers["data"]]

