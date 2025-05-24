from fastapi import HTTPException
from backend_common.dtypes.stripe_dtypes import (
    SubscriptionCreateReq,
    SubscriptionRes,
)
import stripe
from backend_common.database import Database
from backend_common.stripe_backend.customers import fetch_customer
from backend_common.stripe_backend.products import fetch_stripe_product
from backend_common.stripe_backend.prices import calculate_seat_based_pricing
# from backend_common.stripe_backend.prices import calculate_seat_based_p/ricing


# Subscription for individual or team
async def create_subscription(
    subscription_req: SubscriptionCreateReq,
) -> dict:
    # Fetch customer information
    customer = await fetch_customer(user_id=subscription_req.user_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Fetch the product and pricing information
    product = await fetch_stripe_product(subscription_req.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    price_id = product.price_id
    # Determine the price, handling seat adjustments if it's a team package
    if subscription_req.seats > 1:
        # Assume you have pricing logic for seat-based tiers
        price_id = await calculate_seat_based_pricing(
            product, subscription_req.seats
        )
    print("PRICE ID", price_id)
    # Create the subscription
    subscription = stripe.Subscription.create(
        customer=customer['id'],
        items=[
            {
                "price": price_id,
                "quantity": subscription_req.seats,  # Set quantity to the number of seats for team packages
            }
        ],
        default_payment_method=subscription_req.payment_method_id,
        expand=["latest_invoice.payment_intent"],
    )

    # Store subscription details in your database (Optional)
    query = "INSERT INTO stripe_subscriptions (subscription_id, user_id, product_id) VALUES ($1, $2, $3)"
    await Database.execute(
        query,
        subscription.id,
        subscription_req.user_id,
        subscription_req.product_id,
    )

    return subscription.to_dict_recursive()


# Update subscription seats or alter based on business rules
async def update_subscription(subscription_id: str, seats: int) -> dict:
    subscription = stripe.Subscription.retrieve(subscription_id)

    # Adjust the quantity (seats) on the subscription
    updated_subscription = stripe.Subscription.modify(
        subscription_id,
        items=[{"id": subscription["items"]["data"][0].id, "quantity": seats}],
    )

    return updated_subscription.to_dict_recursive()


# Cancel subscription
async def deactivate_subscription(subscription_id: str) -> dict:
    stripe.Subscription.retrieve(subscription_id)
    canceled_subscription = stripe.Subscription.cancel(subscription_id)

    # Optionally, mark the subscription as canceled in your database
    query = "DROP TABLE stripe_subscriptions WHERE subscription_id = $1"
    await Database.execute(query,subscription_id)

    return canceled_subscription.to_dict_recursive()
