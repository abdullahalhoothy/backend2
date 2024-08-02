# run_fetch_transform.py
import asyncio
from database import Database
from storage import (   
    convert_to_serializable,
)

from all_types.myapi_dtypes import MapData

async def main():
    try:
        # Initialize the database pool
        await Database.create_pool()

        print("Starting data fetch and transform process...")

        # Perform a health check
        if not await Database.health_check():
            raise Exception("Database health check failed")

        # Run the fetch and transform process
        query = "SELECT price, additional__WebListing_uri___location_lat, additional__WebListing_uri___location_lng, * FROM public.riyadh_villa_allrooms limit 1"

        # Fetch data from database
        rows = await Database.fetch(query)
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
        # save it back to postgres in a new table as a json object in 1 column
    
        # usea method in storage.py to save to JSON file

        serializable_data=convert_to_serializable( data)
        new_id = await Database.insert_json_data(serializable_data)
        print(f"Inserted data with ID: {new_id}")

        
      


    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        # Always ensure the pool is closed, even if an error occurred
        await Database.close_pool()
        print("Database connection pool closed.")


if __name__ == "__main__":
    # Set up asyncio to use only one worker
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # Use this line if on Windows, comment if on mac or linx
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()