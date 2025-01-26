from storage import get_plan
import asyncio
from backend_common.database import Database
import json
import numpy as np


RADIUS_ZOOM_MULTIPLIER = {
    30000.0: 1000, # 1
    15000.0: 500, # 2
    7500.0: 250, # 3
    3750.0: 125, # 4
    1875.0: 62.5, # 5
    937.5: 31.25, # 6
    468.75: 15.625 # 7
}

def calculate_category_multiplier(index):
    """Calculate category multiplier based on result position."""
    if 0 <= index < 5:  # Category A
        return 1.0
    elif 5 <= index < 10:  # Category B
        return 0.8
    elif 10 <= index < 15:  # Category C
        return 0.6
    else:  # Category D
        return 0.4
    

def get_plan_db_entries(plan_content):
    """Extract plan entries from plan content."""
    if not plan_content:
        return []
    
    plan_entries = []
    for entry in plan_content:
        if not isinstance(entry, str):
            continue
        if "_circle=" not in entry:
            continue
        plan_entries.append(entry.split("_circle=")[0])
    return plan_entries


def add_popularity_score_category(features):
    """Add popularity score category based on quartiles."""
    if not features:
        return features
        
    scores = [f["properties"].get("popularity_score", 0) for f in features]
    if not scores:
        return features
        
    quartiles = np.percentile(scores, [25, 50, 75])
    
    for feature in features:
        score = feature["properties"].get("popularity_score", 0)
        if score >= quartiles[2]:
            category = "Very High"
        elif score >= quartiles[1]:
            category = "High"
        elif score >= quartiles[0]:
            category = "Low"
        else:
            category = "Very Low"
        feature["properties"]["popularity_score_category"] = category
    
    return features


async def process_plan_popularity(plan_name: str):
    """
    Process a plan by its name, updating the database with popularity scores and popularity score categories.
    
    Args:
        plan_name (str): Name of the plan to process (e.g. 'plan_parking_Saudi Arabia_Jeddah')
    """
    plan_content = await get_plan(plan_name)
    if not plan_content:
        print("No plan content found")
        return
        
    plan_entries = get_plan_db_entries(plan_content)
    if not plan_entries:
        print("No valid plan entries found")
        return
        
    plan_entries = [entry + "%" for entry in plan_entries]
    
    query = """
        SELECT * 
        FROM schema_marketplace.datasets
        WHERE filename LIKE ANY($1)
        ORDER BY created_at ASC
    """
    
    try:
        results = await Database.fetch(query, plan_entries)
        print(f"Found datasets: {len(results)}")
        
        if not results:
            print("No matching datasets found")
            return
        
        # Collect all features from all response_data
        all_features = []
        feature_map = {}  # Map to keep track of features by (address, coordinates)
        
        for result in results:
            try:
                response_data = json.loads(result['response_data'])
                features = response_data.get('features', [])
                if not features:
                    print(f"No features found in dataset: {result['filename']}")
                    continue
                    
                for feature in features:
                    address = feature["properties"].get("address")
                    coordinates = tuple(feature["geometry"].get("coordinates", []))
                    if address and coordinates:
                        key = (address, coordinates)
                        feature_map[key] = feature
                        all_features.append(feature)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error processing result {result.get('filename', 'unknown')}: {e}")
                continue
        
        if not all_features:
            print("No features found in any dataset")
            return
            
        # Sort all features globally based on popularity_score
        all_features.sort(key=lambda x: x["properties"].get("popularity_score", 0), reverse=True)
        all_features = add_popularity_score_category(all_features)
        
        sorted_feature_map = {}
        for feature in all_features:
            address = feature["properties"].get("address")
            coordinates = tuple(feature["geometry"].get("coordinates", []))
            sorted_feature_map[(address, coordinates)] = feature
        
        success_count = 0
        
        for result in results:
            try:
                response_data = json.loads(result['response_data'])
                features = response_data.get('features', [])
                
                updated_features = []
                for feature in features:
                    address = feature["properties"].get("address")
                    coordinates = tuple(feature["geometry"].get("coordinates", []))
                    key = (address, coordinates)
                    if key in sorted_feature_map:
                        updated_feature = sorted_feature_map[key]
                        updated_features.append(updated_feature)
                    else:
                        updated_features.append(feature)

                updated_features.sort(key=lambda x: x["properties"].get("popularity_score", 0), reverse=True)
                
                new_response_data = {
                    "type": "FeatureCollection",
                    "features": updated_features,
                    "properties": response_data.get("properties", [])
                }
                
                if "popularity_score" not in new_response_data["properties"]:
                    new_response_data["properties"].append("popularity_score")
                
                if "popularity_score_category" not in new_response_data["properties"]:
                    new_response_data["properties"].append("popularity_score_category")
                
                update_query = """
                    UPDATE schema_marketplace.datasets 
                    SET response_data = $1
                    WHERE filename = $2
                """
                
                await Database.execute(update_query, json.dumps(new_response_data), result['filename'])
                success_count += 1
                print(f"Updated database entry for {result['filename']} - {len(updated_features)} features updated")
                
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error updating database entry {result.get('filename', 'unknown')}: {e}")
                continue
        
        print(f"Database update completed. Successfully updated {success_count} out of {len(results)} datasets")
        
    except Exception as e:
        print(f"An error occurred during execution: {e}")


async def main():
    await process_plan("plan_parking_Saudi Arabia_Jeddah")


if __name__ == "__main__":
    asyncio.run(main())


