from fastapi import HTTPException
from all_types.stripe_dtypes import (
    ProductReq,
    ProductRes,
)
import stripe
from backend_common.database import Database
import json
from backend_common.stripe_backend.prices import create_price


# Stripe Products
async def create_stripe_product(req: ProductReq) -> ProductRes:
    metadata_json = json.dumps(req.metadata.dict(), ensure_ascii=False)
    print(metadata_json)
    print("METADATA JSON")
    # Create a new product in Stripe
    product = stripe.Product.create(
        name=req.name,
        active=req.active,
        description=req.description,
        metadata=req.metadata.dict(),
        images=req.images,
        statement_descriptor=req.statement_descriptor,
        tax_code=req.tax_code,
        unit_label=req.unit_label,
        url=req.url,
    )

    # change the attributes inside the product to a dict

    product_json = dict(product)
    product_json["metadata"] = dict(product.metadata)
    product_json["id"] = (
        product_json["product_id"]
        if "product_id" in product_json
        else product_json["id"]
    )

    try:
        query = "INSERT INTO SubscriptionModels (product_id, name, active, attributes, caption, deactivate_on, description, images, livemode, metadata, package_dimensions, shippable, statement_descriptor, tax_code, unit_label, url) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16) RETURNING *"
        product = await Database.execute(
            query,
            product.id,
            req.name,
            req.active,
            req.attributes,
            req.caption,
            req.deactivate_on,
            req.description,
            req.images,
            product_json["livemode"],
            metadata_json,
            None,
            req.shippable,
            req.statement_descriptor,
            req.tax_code if req.tax_code else None,
            req.unit_label if req.unit_label else None,
            req.url if req.url else None,
        )
    except Exception as e:
        print(e)
        raise HTTPException(status_code=404, detail="Product")

    price = await create_price(req.price, ProductRes(**product_json))

    product_json["price_id"] = price.price_id

    product = await update_stripe_product(
        product_json["id"], ProductRes(**product_json)
    )

    product.price = req.price

    print("PRODUCT IS", product)

    return product


async def update_stripe_product(product_id: str, req: ProductReq) -> ProductRes:
    product = stripe.Product.modify(
        product_id,
        name=req.name,
        active=req.active,
        description=req.description,
        metadata=req.metadata,
        images=req.images,
        statement_descriptor=req.statement_descriptor,
        tax_code=req.tax_code,
        unit_label=req.unit_label,
        url=req.url,
        default_price=req.price_id,
    )

    # Update an existing product in Stripe
    query = "SELECT * FROM SubscriptionModels WHERE product_id = $1"
    product_db = await Database.fetchrow(query, product_id)
    if not product_db:
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        query = "UPDATE SubscriptionModels SET name = $1, active = $2, description = $3, images = $4, livemode = $5, metadata = $6, package_dimensions = $7, shippable = $8, statement_descriptor = $9, tax_code = $10, unit_label = $11, url = $12 WHERE product_id = $13 RETURNING *"

        await Database.execute(
            query,
            req.name,
            req.active,
            req.description,
            req.images,
            product["livemode"],
            json.dumps(req.metadata),
            None,
            req.shippable,
            req.statement_descriptor,
            req.tax_code,
            req.unit_label,
            req.url,
            product_id,
        )
    except Exception as e:
        print(e)
        raise HTTPException(status_code=404, detail="Product")

    return ProductRes(**(dict(product)))


async def delete_stripe_product(product_id: str) -> str:
    # Delete an existing product in Stripe
    response = stripe.Product.delete(product_id)
    try:
        sql = "DELETE FROM SubscriptionModels WHERE product_id = $1"
        await Database.execute(sql, product_id)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=404, detail="Product")
    return f"Product {product_id} deleted"


async def list_stripe_products() -> list[ProductRes]:
    # List all products in Stripe
    products = await Database.fetch("SELECT * FROM SubscriptionModels")

    # Ensure data types and add missing fields
    formatted_products = []
    for product in products:
        formatted_product = {
            "id": str(product["product_id"]),
            "object": product.get("object", "product"),
            "created": product.get("created", 0),
            "updated": product.get("updated", 0),
            "metadata": (
                json.loads(product["metadata"])
                if isinstance(product["metadata"], str)
                else product["metadata"]
            ),
            "active": product.get("active", False),
            "livemode": product.get("livemode", False),
            "name": product.get("name", ""),
        }
        formatted_products.append(ProductRes(**formatted_product))

    return formatted_products


async def fetch_stripe_product(product_id: str) -> ProductRes:
    # Fetch a product from Stripe
    product = stripe.Product.retrieve(product_id)
    product_json = dict(product)
    product_json["metadata"] = dict(product.metadata)
    product_json["price_id"] = product.default_price
    return ProductRes(**product_json)
