from fastapi import HTTPException
from backend_common.dtypes.stripe_dtypes import (
    ProductReq,
    ProductRes,
)
import stripe
from backend_common.database import Database
import json
from backend_common.stripe_backend.prices import create_price


# Stripe Products
async def create_stripe_product(req: ProductReq) -> dict:
    if not req.price:
        raise HTTPException(status_code=400, detail='Price not provided')
    metadata_json = json.dumps(req.metadata.dict(), ensure_ascii=False)
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
        shippable=req.shippable,
    )

    # change the attributes inside the product to a dict
    product_json = dict(product)
    try:
        query = f"INSERT INTO Stripe_Products (product_id) VALUES ('{product.id}') RETURNING *"
        await Database.execute(query)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=404, detail="Unable to create product row")
    price = await create_price(req.price, ProductRes(**product_json))

    product_json["price_id"] = price.price_id
    product = await update_stripe_product(
        product_json["id"], ProductRes(**product_json)
    )

    product.price = req.price

    print("PRODUCT IS", product)

    return product


async def update_stripe_product(product_id: str, req: ProductReq) -> ProductRes:
    query = "SELECT * FROM Stripe_Products WHERE product_id = $1"
    product_db = await Database.fetchrow(query, product_id)
    if not product_db:
        raise HTTPException(status_code=404, detail="Product not found")
    metadata = req.metadata if isinstance(req.metadata, dict) else req.metadata.dict()
    product = stripe.Product.modify(
        product_id,
        name=req.name,
        active=req.active,
        description=req.description,
        metadata=metadata,
        images=req.images,
        statement_descriptor=req.statement_descriptor,
        tax_code=req.tax_code,
        unit_label=req.unit_label,
        url=req.url,
        default_price=req.price_id,
    )
    product = product.to_dict_recursive()
    product.update(price_id=req.price_id)
    return product


async def delete_stripe_product(product_id: str) -> dict:
    # Delete an existing product in Stripe
    response = stripe.Product.modify(product_id, active=False)
    try:
        sql = "DELETE FROM Stripe_Products WHERE product_id = $1"
        await Database.execute(sql, product_id)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=404, detail="Product")
    return response.to_dict_recursive()


async def list_stripe_products() -> list[dict]:
    # List all products in Stripe
    products =  stripe.Product.list(limit=1_000).to_dict_recursive()
    # Ensure data types and add missing fields
    return products['data']


async def fetch_stripe_product(product_id: str) -> ProductRes:
    # Fetch a product from Stripe
    product = stripe.Product.retrieve(product_id)
    product_json = dict(product)
    product_json["metadata"] = dict(product.metadata)
    product_json["price_id"] = product.default_price
    return ProductRes(**product_json)
