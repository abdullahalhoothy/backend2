from geo_std_utils import get_point_at_distance
from parrallel_create_duplicate_rules import create_duplicate_rules
from use_json import use_json
import asyncio
from backend_common.database import Database
import json
import numpy as np
import math
import pandas as pd
from backend_common.logging_wrapper import apply_decorator_to_module
import logging
from geopy.distance import geodesic

import json
from geopy.distance import geodesic

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


RADIUS_ZOOM_MULTIPLIER = {
    30000.0: 1000,  # 1
    15000.0: 500,  # 2
    7500.0: 250,  # 3
    3750.0: 125,  # 4
    1875.0: 62.5,  # 5
    937.5: 31.25,  # 6
    468.75: 15.625,  # 7
}
DEDUPLICATE_RULES_PATH = 'Backend/layer_category_country_city_matching/full_data_plans/duplicate_rules.json'
with open(DEDUPLICATE_RULES_PATH, "r") as f:
    DEDUPLICATE_RULES = json.load(f)

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


async def get_plan(plan_name):
    file_path = (
        f"Backend/layer_category_country_city_matching/full_data_plans/{plan_name}.json"
    )
    # use json file
    json_content = await use_json(file_path, "r")
    return json_content


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
                response_data = json.loads(result["response_data"])
                features = response_data.get("features", [])
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
                print(
                    f"Error processing result {result.get('filename', 'unknown')}: {e}"
                )
                continue

        if not all_features:
            print("No features found in any dataset")
            return

        # Sort all features globally based on popularity_score
        all_features.sort(
            key=lambda x: x["properties"].get("popularity_score", 0), reverse=True
        )
        all_features = add_popularity_score_category(all_features)

        sorted_feature_map = {}
        for feature in all_features:
            address = feature["properties"].get("address")
            coordinates = tuple(feature["geometry"].get("coordinates", []))
            sorted_feature_map[(address, coordinates)] = feature

        success_count = 0

        for result in results:
            try:
                response_data = json.loads(result["response_data"])
                features = response_data.get("features", [])

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

                updated_features.sort(
                    key=lambda x: x["properties"].get("popularity_score", 0),
                    reverse=True,
                )

                new_response_data = {
                    "type": "FeatureCollection",
                    "features": updated_features,
                    "properties": response_data.get("properties", []),
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

                await Database.execute(
                    update_query, json.dumps(new_response_data), result["filename"]
                )
                success_count += 1
                print(
                    f"Updated database entry for {result['filename']} - {len(updated_features)} features updated"
                )

            except (json.JSONDecodeError, KeyError) as e:
                print(
                    f"Error updating database entry {result.get('filename', 'unknown')}: {e}"
                )
                continue

        print(
            f"Database update completed. Successfully updated {success_count} out of {len(results)} datasets"
        )

    except Exception as e:
        print(f"An error occurred during execution: {e}")


def cover_circle_with_seven_circles_helper(center, radius_km):
    distance = radius_km * math.sqrt(3) / 2

    outer_centers = []
    for i in range(6):
        angle = i * 60  # 6 circles around at equal angles
        outer_center = get_point_at_distance(center[::-1], angle, distance)
        outer_centers.append((outer_center.longitude, outer_center.latitude))

    return [center] + outer_centers


def cover_circle_with_seven_circles(
    center: tuple, radius: float, min_radius=2, is_center_circle=False
) -> dict:
    """
    Calculate the centers and radii of seven circles covering a larger circle, recursively.
    """
    small_radius = 0.5 * radius
    if (is_center_circle and small_radius < 0.5) or (
        not is_center_circle and small_radius < 1
    ):
        return {
            "center": center,
            "radius": radius,
            "sub_circles": [],
            "is_center": is_center_circle,
        }

    all_centers = cover_circle_with_seven_circles_helper(center, radius)

    sub_circles = []
    for i, c in enumerate(all_centers):
        is_center = i == 0
        sub_circle = cover_circle_with_seven_circles(
            c, small_radius, min_radius, is_center
        )
        sub_circles.append(sub_circle)

    return {
        "center": center,
        "radius": radius,
        "sub_circles": sub_circles,
        "is_center": is_center_circle,
    }


def create_string_list(
    circle_hierarchy, type_string, text_search, include_hierarchy=False
):
    result = []
    circles_to_process = [(circle_hierarchy, "1")]
    total_circles = 0

    while circles_to_process:
        circle, number = circles_to_process.pop(0)
        total_circles += 1

        lat, lng = circle["center"]
        radius = circle["radius"]

        circle_string = f"{lat}_{lng}_{radius * 1000}_{type_string}"
        if text_search != "" and text_search is not None:
            circle_string = circle_string + f"_{text_search}"

        center_marker = "*" if circle["is_center"] else ""
        circle_string += f"_circle={number}{center_marker}_circleNumber={total_circles}"

        result.append(circle_string)

        for i, sub_circle in enumerate(circle["sub_circles"], 1):
            new_number = f"{number}.{i}" if number else f"{i}"
            circles_to_process.append((sub_circle, new_number))

    return result


class Counter:
    def __init__(self) -> None:
        self.value = 0

    def get_value(self):
        self.value += 1
        return self.value


class Circle:
    def __init__(self, center, radius, level, id, counter, is_center, min_radius=2):
        self.counts = counter.get_value()
        self.center = np.round(center[0], 4), np.round(center[1], 4)
        self.radius = radius
        self.level = level
        self.id = id
        self.is_center = is_center
        if radius > min_radius:
            self.children = cover_circle_with_seven_circles_helper(
                self.center, self.radius
            )
            self.children = [
                Circle(
                    child,
                    self.radius / 2.0,
                    level + 1,
                    id + "." + str(index),
                    counter,
                    True if index == 1 else False,
                    min_radius=min_radius,
                )
                for index, child in enumerate(self.children, 1)
            ]
        else:
            self.children = []

    def get_dct(self):
        return {
            "lng": str(self.center[0]),
            "lat": str(self.center[1]),
            "radius": str(self.radius * 1000),
            "level": str(self.level),
            "id": str(self.id),
            "counter": str(self.counts),
            "children": self.children,
            "is_center": "*" if self.is_center else "",
        }



def filter_circles(circle_list):
    # Extract the first circle's details (lon, lat, radius)
    first_circle = circle_list[0]
    parts = first_circle.split('_')    
    lon0 = float(parts[0])  # First part is longitude
    lat0 = float(parts[1])  # Second part is latitude
    radius0 = float(parts[2]) * 1.1 # Third part is radius in meters

    
    filtered = [first_circle]
    center0 = (lat0, lon0)  # Correct order for geopy (lat, lon)
    
    for circle_str in circle_list[1:]:
        current_parts = circle_str.split('_')       
        current_lon = float(current_parts[0])  # Longitude is first part
        current_lat = float(current_parts[1])  # Latitude is second part
        
        current_center = (current_lat, current_lon)  # Correct order for geopy
        distance = geodesic(center0, current_center).meters
        
        if distance <= radius0:
            filtered.append(circle_str)

    return filtered


def process_circles(input_strings):
    duplicate_rules = DEDUPLICATE_RULES
    # optimized_create_duplicate_rules(r'G:\My Drive\Personal\Work\offline\Jupyter\Git\s_locator\my_middle_API\Backend\layer_category_country_city_matching\full_data_plans\plan_atm_Saudi Arabia_Jeddah.json')

    # parrallel_create_duplicate_rules(r'G:\My Drive\Personal\Work\offline\Jupyter\Git\s_locator\my_middle_API\Backend\layer_category_country_city_matching\full_data_plans\plan_atm_Saudi Arabia_Jeddah.json')

    # create_duplicate_rules(r'G:\My Drive\Personal\Work\offline\Jupyter\Git\s_locator\my_middle_API\Backend\layer_category_country_city_matching\full_data_plans\plan_atm_Saudi Arabia_Jeddah.json')
    # base_rules = {
    #     '2.5': '1.2',
    #     '3.6': '1.3',
    #     '3.7': '2.4',
    #     '4.2': '3.5',
    #     '4.7': '1.4',
    #     '5.2': '1.5',
    #     '5.3': '4.6',
    #     '6.3': '1.6',
    #     '6.4': '5.7',
    #     '7.3': '2.6',
    #     '7.4': '1.7',
    #     '7.5': '6.2'
    # }
    # # Generate all combinations of rules
    # duplicate_rules = {}
    
    # # For patterns like 1.2.5 -> 1.1.2
    # for x in range(1, 8):
    #     for key, value in base_rules.items():
    #         source = f"{x}.{key}"
    #         target = f"{x}.{value}"
    #         duplicate_rules[source] = target
    
    # # For patterns like x.y.2.5 -> x.y.1.2
    # for x in range(1, 8):
    #     for y in range(1, 8):
    #         for key, value in base_rules.items():
    #             source = f"{x}.{y}.{key}"
    #             target = f"{x}.{y}.{value}"
    #             duplicate_rules[source] = target
    
    # # For patterns like x.y.z.2.5 -> x.y.z.1.2
    # for x in range(1, 8):
    #     for y in range(1, 8):
    #         for z in range(1, 8):
    #             for key, value in base_rules.items():
    #                 source = f"{x}.{y}.{z}.{key}"
    #                 target = f"{x}.{y}.{z}.{value}"
    #                 duplicate_rules[source] = target

    result = []
    removed_children = {}  # To keep track of removed children for each parent
    
    for s in input_strings:
        parts = s.split('_')
        circle = None
        for part in parts:
            if part.startswith('circle='):
                circle = part.split('=')[1].rstrip('*')
                break
        

        # Check if it's a child of any circle in duplicate_rules
        is_child = False
        for parent in duplicate_rules.keys():
            if circle.startswith(parent + '.'):
                is_child = True
                if parent not in removed_children:
                    removed_children[parent] = []
                removed_children[parent].append(circle)
                break
                
        if is_child:
            continue

        # Add _duplicateWith for specified circles
        if circle in duplicate_rules:
            # modified_string = s + f"_duplicateWith={duplicate_rules[circle]}"
            # result.append(modified_string)
            continue
        else:
            result.append(s)

    return result

async def create_plan(lng, lat, radius, boolean_query, text_search):
    text = boolean_query + "_" + text_search
    text = text.strip("_")
    counter = Counter()
    circle_hierarchy = Circle(
        (lng, lat), radius / 1000, 1, id="1", counter=counter, is_center=True
    )
    db_dict = {}

    def get_data(c:Circle):
        data = c.get_dct()
        db_dict[(data["lng"], data["lat"], data["radius"], data["id"])] = data
        for child in data["children"]:
            get_data(child)

    get_data(circle_hierarchy)

    db = pd.DataFrame(db_dict.values())
    order = (
        db[["radius", "counter"]]
        .astype("float")
        .assign(counter=lambda x: -x.counter)
        .sort_values(["radius", "counter"], ascending=False)
    )
    db = db.loc[order.index]
    db["p_counter"] = np.arange(0, db.shape[0]) + 1

    string_list = (
        db["lng"]
        + "_"
        + db["lat"]
        + "_"
        + db["radius"]
        + "_"
        + text
        + "_"
        + "circle="
        + db["id"]
        + db["is_center"]
        + "_"
        + "circleNumber="
        + db["p_counter"].astype("str")
    )
    string_list = string_list.values.tolist()
    # string_list_plan = create_string_list(circle_hierarchy, boolean_query, text_search)
    string_list = filter_circles(string_list)
    string_list = process_circles(string_list)
    string_list.append("end of search plan")
    return string_list


async def save_plan(plan_name, plan):
    file_path = (
        f"Backend/layer_category_country_city_matching/full_data_plans/{plan_name}.json"
    )
    await use_json(file_path, "w", plan)


# Apply the decorator to all functions in this module
apply_decorator_to_module(logger)(__name__)
