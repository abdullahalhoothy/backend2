from datetime import datetime
from all_types.stripe_dtypes import ProductReq, PriceReq, PriceRes, ProductRes
import stripe
from backend_common.database import Database


# Create a new price
async def create_price(price_req: PriceReq, product_req: ProductReq) -> PriceRes:
    if price_req.pricing_type == "flat":
        stripe_price = stripe.Price.create(
            product=product_req.id,
            currency=price_req.currency,
            unit_amount=price_req.unit_amount,
            recurring={
                "interval": price_req.recurring_interval,
                "interval_count": price_req.recurring_interval_count,
                "usage_type": "licensed",
            },
        )
    elif price_req.pricing_type == "tier":
        stripe_price = stripe.Price.create(
            product=product_req.id,
            currency=price_req.currency,
            tiers=[
                {
                    "up_to": price_req.included_seats,
                    "unit_amount": price_req.base_amount,
                },
                {"up_to": "inf", "unit_amount": price_req.additional_seat_price},
            ],
            recurring={
                "interval": price_req.recurring_interval,
                "interval_count": price_req.recurring_interval_count,
                "usage_type": "licensed",
            },
            tiers_mode="volume",
            billing_scheme="tiered",
        )
    else:
        raise ValueError("Invalid pricing type")

    query = """
    INSERT INTO prices (
        price_id, product_id, currency, unit_amount, base_amount, included_seats, additional_seat_price, recurring_interval, recurring_interval_count, created_at, updated_at, pricing_type
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12) RETURNING *
    """
    created_at = datetime.now()
    updated_at = created_at

    price = await Database.execute(
        query,
        stripe_price.id,
        product_req.id,
        price_req.currency,
        price_req.unit_amount,
        price_req.base_amount,
        price_req.included_seats,
        price_req.additional_seat_price,
        price_req.recurring_interval,
        price_req.recurring_interval_count,
        created_at,
        updated_at,
        price_req.pricing_type,
    )
    stripe_price_json = dict(stripe_price)
    stripe_price_json["product_id"] = product_req.id
    stripe_price_json["price_id"] = stripe_price_json["id"]
    stripe_price_json["created_at"] = created_at
    stripe_price_json["updated_at"] = updated_at
    stripe_price_json["recurring_interval"] = price_req.recurring_interval
    stripe_price_json["recurring_interval_count"] = price_req.recurring_interval_count

    return PriceRes(**stripe_price_json)


# List all prices
async def list_prices() -> list[PriceRes]:
    query = "SELECT * FROM prices"
    prices = await Database.fetch_all(query)
    return [PriceRes(**price) for price in prices]


# Update an existing price


async def update_price(price_id: str, price_req: PriceReq) -> PriceRes:
    if price_req.pricing_type == "flat":
        stripe_price = stripe.Price.modify(
            price_id,
            unit_amount=price_req.unit_amount,
            recurring={
                "interval": price_req.recurring_interval,
                "interval_count": price_req.recurring_interval_count,
                "usage_type": "licensed",
            },
        )
    elif price_req.pricing_type == "tier":
        stripe_price = stripe.Price.modify(
            price_id,
            tiers=[
                {
                    "up_to": price_req.included_seats,
                    "unit_amount": price_req.base_amount,
                },
                {"up_to": "inf", "unit_amount": price_req.additional_seat_price},
            ],
            recurring={
                "interval": price_req.recurring_interval,
                "interval_count": price_req.recurring_interval_count,
                "usage_type": "licensed",
            },
            billing_scheme="tiered",
        )
    else:
        raise ValueError("Invalid pricing type")

    query = """
    UPDATE prices
    SET
        currency = $1,
        unit_amount = $2,
        base_amount = $3,
        included_seats = $4,
        additional_seat_price = $5,
        recurring_interval = $6,
        recurring_interval_count = $7,
        updated_at = $8
    WHERE price_id = $9
    RETURNING *
    """
    updated_at = datetime.now()

    price = await Database.execute(
        query,
        price_req.currency,
        price_req.unit_amount,
        price_req.base_amount,
        price_req.included_seats,
        price_req.additional_seat_price,
        price_req.recurring_interval,
        price_req.recurring_interval_count,
        updated_at,
        price_id,
    )

    return PriceRes(**price)


# Delete a price
async def delete_price(price_id: str) -> None:
    stripe.Price.delete(price_id)

    query = "DELETE FROM prices WHERE price_id = $1"
    await Database.execute(query, price_id)


# add a new seat
async def add_seat_to_price(price_id: str, seats: int) -> PriceRes:
    price = stripe.Price.retrieve(price_id)
    if price["billing_scheme"] != "tiered":
        raise ValueError("Price is not tiered")

    updated_price = stripe.Price.modify(
        price_id,
        tiers=[
            {
                "up_to": price["tiers"][-1]["up_to"] + seats,
                "unit_amount": price["tiers"][-1]["unit_amount"],
            }
        ],
    )

    query = """
    UPDATE prices
    SET
        included_seats = $1,
        updated_at = $2
    WHERE price_id = $3
    RETURNING *
    """
    updated_at = datetime.now()

    price = await Database.execute(
        query, updated_price["tiers"][-1]["up_to"], updated_at, price_id
    )

    return PriceRes(**price)


# Subscriptions
async def calculate_seat_based_pricing(product: ProductRes, seats: int) -> str:
    # Fetch the product pricing details from Stripe or database
    # Adjust price based on seat count (if you are using tiered pricing)

    price = None
    if seats > 1 and seats > int(product.metadata["seats"]):
        # Create tiered pricing for multiple seats
        price = stripe.Price.create(
            product=product.id,
            currency="usd",
            unit_amount=product.metadata["base_amount"]
            + product.metadata["additional_seat_price"]
            * int(seats - int(product.metadata["seats"])),
            recurring={"interval": "month"},
            tiers=[
                {
                    "up_to": product.metadata["seats"],  # Base package seats
                    "unit_amount": product.metadata["base_amount"],
                },
                {
                    "up_to": "inf",
                    "unit_amount": product.metadata["additional_seat_price"],
                },
            ],
        )
    else:
        price = product.default_price

    return price.id
