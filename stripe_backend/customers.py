from datetime import datetime
from fastapi import HTTPException
from all_types.stripe_dtypes import (
    CustomerReq,
    CustomerRes,
)
import stripe
from database import Database
import json

# customer functions
async def create_customer(customer_req: CustomerReq) -> CustomerRes:
    # Create a new customer in Stripe
    customer = stripe.Customer.create(
        name=customer_req.name,
        email=customer_req.email,
        description=customer_req.description,
        phone=customer_req.phone,
        address=customer_req.address.dict(),
        metadata=customer_req.metadata,
    )

    # Save the customer in the database
    query = "INSERT INTO stripe_customers (user_id, customer_id, name, email, description, phone, address, metadata, created, invoice_prefix) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10) RETURNING *"
    customer_json = dict(customer)
    customer_json["metadata"] = dict(customer.metadata)
    customer_json["address"] = dict(customer.address)

    customer = await Database.execute(
        query,
        customer_req.user_id,
        customer.id,
        customer.name,
        customer.email,
        customer.description,
        customer.phone,
        json.dumps(customer_json["address"]),
        json.dumps(customer_json["metadata"]),
        datetime.now(),
        "s_locator_",
    )

    customer_json["user_id"] = customer_req.user_id

    return CustomerRes(**customer_json)


async def fetch_customer(user_id: str) -> CustomerRes:
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


async def update_customer(customer_req: CustomerReq) -> CustomerRes:
    stripe_customer = stripe.Customer.modify(
        customer_req.user_id,
        name=customer_req.name,
        email=customer_req.email,
        description=customer_req.description,
        phone=customer_req.phone,
        address=customer_req.address.dict(),
        metadata=customer_req.metadata.dict(),
    )

    query = "UPDATE stripe_customers SET name = $1, email = $2, description = $3, phone = $4, address = $5, metadata = $6 WHERE user_id = $7 RETURNING *"

    customer = await Database.execute(
        query,
        customer_req.name,
        customer_req.email,
        customer_req.description,
        customer_req.phone,
        customer_req.address.dict(),
        customer_req.metadata.dict(),
        customer_req.user_id,
    )

    return CustomerRes(**customer)


async def delete_customer(user_id: str) -> dict:
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

