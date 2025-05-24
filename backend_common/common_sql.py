from dataclasses import dataclass


@dataclass
class CommonSql:
    pass
    # fetch_customer_id_by_user_id__stripe_query = (
    #     "SELECT customer_id FROM stripe_customers WHERE user_id = $1"
    # )

    # delete_customer_strip_query = (
    #     """DELETE FROM stripe_customers WHERE customer_id = $1"""
    # )

    # firebase_strip_mapping: str = """
    #     INSERT INTO stripe_customers (user_id, customer_id) VALUES ($1, $2)
    #     ON CONFLICT (user_id) DO UPDATE
    #     SET customer_id = $2;
    # """
