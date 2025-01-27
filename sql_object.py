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

    census_w_bounding_box: str = """SELECT * FROM "schema_marketplace".census
                                WHERE population is not Null 
                                AND latitude BETWEEN $1 AND $2 
                                AND longitude BETWEEN $3 AND $4
                                AND zoom_level = $5;
                                """
    # population_w_bounding_box: str = """SELECT * FROM "schema_marketplace".housing
    #                                 where latitude BETWEEN $1 AND $2 AND longitude BETWEEN $3 AND $4 LIMIT 20;
    #                                 """
    # population_w_bounding_box: str = """SELECT * FROM "schema_marketplace".household
    #                                 where latitude BETWEEN $1 AND $2 AND longitude BETWEEN $3 AND $4 LIMIT 20;
    #                                 """
    economic_w_bounding_box: str = """SELECT * FROM "schema_marketplace".economic
                                    where latitude BETWEEN $1 AND $2 AND longitude BETWEEN $3 AND $4 LIMIT 20;
                                    """
    canada_commercial_w_bounding_box_and_property_type: str = """
        SELECT address, price, price_description, property_type, city, description, region_stats_summary, latitude, longitude
        FROM "schema_marketplace".canada_commercial_properties
        WHERE lower(property_type) LIKE '%' || lower($1) || '%'
            AND latitude BETWEEN $2 AND $3
            AND longitude BETWEEN $4 AND $5
        LIMIT $6 OFFSET $7;
    """

    saudi_real_estate_w_bounding_box_and_category: str = """
        SELECT url, price, city, latitude, longitude, category FROM "schema_marketplace".saudi_real_estate
        WHERE "category" = ANY($1)
            AND latitude BETWEEN $2 AND $3
            AND longitude BETWEEN $4 AND $5
        LIMIT $6 OFFSET $7;
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
    load_dataset_with_timestamp: str = """
    SELECT response_data, created_at
    FROM "schema_marketplace"."datasets"
    WHERE filename = $1;
    """

    delete_dataset: str = """
    DELETE FROM "schema_marketplace"."datasets"
    WHERE filename = $1;
    """