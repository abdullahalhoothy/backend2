# run_fetch_transform.py
import asyncio
from database import Database
from storage import (   
    save_to_json_file
)

from scripts.database_transformation import (   
   insert_json_data,
   create_riyadh_villa_allrooms_json_table,
   create_feature_collection
)

async def main():
    try:
        # Initialize the database pool
        await Database.create_pool()

        print("Starting data fetch and transform process...")

        # Perform a health check
        if not await Database.health_check():
            raise Exception("Database health check failed")

        # Run the fetch and transform process
        query = "SELECT price, additional__WebListing_uri___location_lat, additional__WebListing_uri___location_lng, * FROM public.riyadh_villa_allrooms limit 10"


        # Fetch data from database
        rows = await Database.fetch(query)  
        
        serializable_data = create_feature_collection(rows)
        
        # await create_riyadh_villa_allrooms_json_table()
        new_id = await insert_json_data("riyadh_villa_allrooms_json",serializable_data)
        print(f"Inserted data with ID: {new_id}")
        await save_to_json_file("riyadh_villa_allrooms",new_id, serializable_data)
       

        
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