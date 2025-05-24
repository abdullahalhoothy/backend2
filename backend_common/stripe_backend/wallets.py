from fastapi import HTTPException
import stripe
from backend_common.stripe_backend.customers import fetch_customer
from backend_common.dtypes.stripe_dtypes import TopUpWalletReq,DeductWalletReq


# wallet functions
async def top_up_wallet(req: TopUpWalletReq):
    # Access the parameters from the request body
    user_id = req.user_id
    amount = int(req.amount)
    # Fetch the customer from Stripe
    customer = await fetch_customer(user_id=user_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Add funds to the customer's balance in Stripe
    # The amount should be in cents (for example, $10 = 1000)
    adjustment = stripe.Customer.create_balance_transaction(
        customer['id'],
        amount=amount,  # Positive amount to increase balance
        currency="usd",
        description=(
            "Added funds to wallet" if int(amount) > 0 else "Deducted funds from wallet"
        ),
    )

    return  dict(adjustment)


async def fetch_wallet(user_id: str) -> dict:
    # Fetch the customer from Stripe
    customer = await fetch_customer(user_id=user_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Get the customer's current balance in Stripe
    balance = customer['balance']

    return {
        "customer_id": customer['id'],
        "balance": balance / 100.0,  # Stripe returns balance in cents
        "currency": "usd",
    }

async def deduct_from_wallet(req: DeductWalletReq):
    # Access the parameters from the request body
    user_id = req.user_id
    amount = int(req.amount)
    # Fetch the customer from Stripe
    customer = await fetch_customer(user_id=user_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Check if customer has sufficient balance
    if customer['balance'] < amount:
        raise HTTPException(
            status_code=400, 
            detail="Insufficient balance in wallet"
        )
    
    # Deduct funds from the customer's balance in Stripe
    # Note: For deductions, we pass a negative amount
    adjustment = stripe.Customer.create_balance_transaction(
        customer['id'],
        amount=-amount,  # Negative amount to decrease balance
        currency="usd",
        description="Deducted funds from wallet"
    )
    
    return dict(adjustment)