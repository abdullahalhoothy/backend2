# database_transformation.py
import json
from database import Database
from all_types.myapi_dtypes import MapData
from storage import (   
    convert_to_serializable,
)
async def create_riyadh_villa_allrooms_json_table()-> None:
        create_table_query = """
        CREATE TABLE IF NOT EXISTS riyadh_villa_allrooms_json (
            id TEXT PRIMARY KEY,
            data JSONB
        );
        """
        await Database.execute(create_table_query)

async def insert_json_data( table_name: str, json_data: dict, id_column: str = 'id', data_column: str = 'data')-> str:
    insert_query = f"""
    INSERT INTO {table_name} ({id_column}, {data_column})  
    VALUES ($1, $2)
    ON CONFLICT ({id_column}) DO NOTHING
    """
    
    # Extract coordinates from the first feature
    if json_data['type'] == 'FeatureCollection' and json_data['features']:
        coordinates = json_data['features'][0]['geometry']['coordinates']
        if len(coordinates) == 2:
            custom_id = f"{coordinates[0]}_{coordinates[1]}"
            json_str = json.dumps(json_data)  # Convert dict to JSON string
            await Database.execute(insert_query, custom_id, json_str)
            return custom_id
        else:
            raise ValueError("Invalid coordinates format")
    else:
        raise ValueError("Invalid JSON structure")
    
   

def create_feature_collection (rows: list)-> MapData:
    keys=  list(dict(rows[0]).keys())
      
    # do your transofmration       
    features=[]
    for row in rows:
        lng = row["additional__weblisting_uri___location_lat"]
        lat = row["additional__weblisting_uri___location_lng"]
        # keys without lat and lng
        customKeys = [x for x in keys if x != "additional__weblisting_uri___location_lat" and x != "additional__weblisting_uri___location_lng"]


        feature = {
            'type': 'Feature',
            'properties': 
                {key: row[key] for key in customKeys}
            ,
            'geometry': {
                'type': 'Point',
                'coordinates': [lng, lat]
            }
        }
        features.append(feature)

    data = MapData(
        type='FeatureCollection',
        features=features
    )
    # usea method in storage.py to save to JSON file
    serializable_data=convert_to_serializable(data)
    return serializable_data

