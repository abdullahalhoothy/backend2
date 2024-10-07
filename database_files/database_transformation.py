# database_transformation.py
import json
from backend_common.database import Database
from all_types.response_dtypes import MapData
from storage import (
    convert_to_serializable,
)


async def insert_geojson_to_table(
    table_name: str, json_data: dict, id_column: str = "id", data_column: str = "data"
) -> list[str]:
    # Create table if it doesn't exist
    create_table_query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            {id_column} TEXT PRIMARY KEY,
            {data_column} JSONB
        );
        """
    await Database.execute(create_table_query)

    # Prepare the upsert query
    upsert_query = f"""
        INSERT INTO {table_name} ({id_column}, {data_column})  
        VALUES 
        """

    values = []
    inserted_or_updated_ids = []
    params = []

    if json_data["type"] == "FeatureCollection" and json_data["features"]:
        for i, feature in enumerate(json_data["features"]):
            coordinates = feature["geometry"]["coordinates"]
            if len(coordinates) == 2:
                custom_id = f"{coordinates[0]}_{coordinates[1]}"
                feature_json = json.dumps(feature)
                values.append(f"(${i * 2 + 1}, ${i * 2 + 2})")
                params.extend([custom_id, feature_json])
                inserted_or_updated_ids.append(custom_id)
            else:
                print(f"Skipping feature with invalid coordinates: {coordinates}")

        if not inserted_or_updated_ids:
            raise ValueError("No valid features found in the GeoJSON data")

        # Complete the upsert query
        upsert_query += ",".join(values)
        upsert_query += f" ON CONFLICT ({id_column}) DO UPDATE SET {data_column} = EXCLUDED.{data_column}"

        # Execute the query with all the data
        await Database.execute(upsert_query, *params, save_sql_script=True)

        return inserted_or_updated_ids
    else:
        raise ValueError("Invalid JSON structure")


def create_feature_collection(rows: list) -> MapData:
    keys = list(dict(rows[0]).keys())

    # do your transofmration
    features = []
    for row in rows:
        lng = row["additional__weblisting_uri___location_lat"]
        lat = row["additional__weblisting_uri___location_lng"]
        # keys without lat and lng
        customKeys = [
            x
            for x in keys
            if x != "additional__weblisting_uri___location_lat"
            and x != "additional__weblisting_uri___location_lng"
        ]

        feature = {
            "type": "Feature",
            "properties": {key: row[key] for key in customKeys},
            "geometry": {"type": "Point", "coordinates": [lat, lng]},
        }
        features.append(feature)

    data = MapData(type="FeatureCollection", features=features)
    # usea method in storage.py to save to JSON file
    serializable_data = convert_to_serializable(data)
    return serializable_data
