from fastapi import HTTPException
import stripe
from backend_common.stripe_backend.customers import fetch_customer


# wallet functions
async def charge_wallet(user_id: str, amount: int) -> dict:
    # Fetch the customer from Stripe
    customer = await fetch_customer(user_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Add funds to the customer's balance in Stripe
    # The amount should be in cents (for example, $10 = 1000)
    adjustment = stripe.Customer.create_balance_transaction(
        customer.id,
        amount=amount,  # Positive amount to increase balance
        currency="usd",
        description=(
            "Added funds to wallet" if int(amount) > 0 else "Deducted funds from wallet"
        ),
    )

    return {
        "message": "Wallet charged" if int(amount) > 0 else "Wallet deducted",
        "balance_transaction": adjustment,
    }


async def fetch_wallet(user_id: str) -> dict:
    # Fetch the customer from Stripe
    customer = await fetch_customer(user_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Get the customer's current balance in Stripe
    balance = stripe.Customer.retrieve(customer.id)["balance"]

    return {
        "customer_id": customer.id,
        "balance": balance / 100.0,  # Stripe returns balance in cents
        "currency": "usd",
    }
