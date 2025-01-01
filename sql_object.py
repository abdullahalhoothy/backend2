from dataclasses import dataclass


@dataclass
class SqlObject:

    upsert_user_profile_query: str = """
        INSERT INTO user_data
        (user_id, prdcer_dataset, prdcer_lyrs, prdcer_ctlgs, draft_ctlgs)
            VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (user_id) DO UPDATE
        SET prdcer_dataset = $2, 
            prdcer_lyrs = $3, 
            prdcer_ctlgs = $4, 
            draft_ctlgs = $5; 
    """
    load_user_profile_query: str = """SELECT * FROM user_data WHERE user_id = $1;"""

    population_w_city: str = """SELECT * FROM "schema_marketplace".population
                                    where "city" = $1;
                                    """
    housing_w_city: str = """SELECT * FROM "schema_marketplace".housing
                                    where "city" = $1;
                                    """
    household_w_city: str = """SELECT * FROM "schema_marketplace".household
                                    where "city" = $1;
                                    """
    economic_w_city: str = """SELECT * FROM "schema_marketplace".economic
                                    where "city" = $1;
                                    """
    canada_commercial_w_city: str = """
        SELECT address, price, price_description, property_type, city, description, region_stats_summary, latitude, longitude
        FROM "schema_marketplace".canada_commercial_properties
        WHERE lower(property_type) LIKE '%' || lower($1) || '%' AND unaccent("city") ILIKE unaccent($2)
        ORDER BY similarity(unaccent("city"), unaccent($2)) DESC LIMIT 20;
    """

    saudi_real_estate_w_city_and_category: str = """
        SELECT url, price, city, latitude, longitude FROM "schema_marketplace".saudi_real_estate
        WHERE "city" = $1 AND "category" = $2 LIMIT 20;
    """
    create_datasets_table: str = """
    CREATE SCHEMA IF NOT EXISTS "schema_marketplace";
    
    CREATE TABLE IF NOT EXISTS "schema_marketplace"."datasets" (
        filename TEXT PRIMARY KEY,
        request_data JSONB,
        response_data JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    store_dataset: str = """
    INSERT INTO "schema_marketplace"."datasets" 
    (filename, request_data, response_data, created_at)
    VALUES ($1, $2, $3, $4)
    ON CONFLICT (filename) 
    DO UPDATE SET 
        request_data = $2,
        response_data = $3,
        created_at = $4;
    """
    
    load_dataset: str = """
    SELECT response_data 
    FROM "schema_marketplace"."datasets" 
    WHERE filename = $1;
    """
