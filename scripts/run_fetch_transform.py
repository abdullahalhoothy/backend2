# run_fetch_transform.py
import asyncio
from backend_common.database import Database


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

        # Fetch data from backend_common.database
        rows = await Database.fetch(query)

        # do your transofmration
        transformed_data = [
            {
                "id": row['id'],
                "name": row['name'],
                # Add more fields as needed
            }
            for row in rows
        ]
        # save it back to postgres in a new table as a json object in 1 column

        # usea method in storage.py to save to JSON file



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