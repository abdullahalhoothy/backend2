import logging
import math
from typing import List, Tuple

import requests

from all_types.myapi_dtypes import ReqLocation
from config_factory import get_conf
from logging_wrapper import apply_decorator_to_module

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
CONF = get_conf()




async def fetch_from_google_maps_api(req: ReqLocation):


    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": CONF.api_key,
        "X-Goog-FieldMask": CONF.google_fields,
    }
    data = {
        "includedTypes": [req.includedTypes],
        "excludedTypes": [req.excludedTypes],
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": req.lat,
                    "longitude": req.lng
                },
                "radius": req.radius
            }
        },
    }

    response = requests.post(CONF.nearby_search, headers=headers, json=data)
    if response.status_code == 200:
        response_data = response.json()
        results = response_data.get("places", [])

        return results, ''
    else:
        print("Error:", response.status_code)
        return [], None


# import json
# with open("Backend/datasets/111.json", "w") as file:
#     json.dump(results, file, indent=4)


async def old_fetch_from_google_maps_api(req: ReqLocation):
    lat, lng, radius, place_type = req.lat, req.lng, req.radius, req.type
    place_type = place_type.lower().replace(" ", "_")
    api_key = CONF.api_key
    radius = 1000

    base_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

    params = {
        "key": api_key,
        "location": f"{lat},{lng}",
        "radius": radius,
        "type": place_type,
    }

    all_results = []
    next_page_token = None

    while True:
        if next_page_token:
            params["pagetoken"] = next_page_token

        response = requests.get(base_url, params=params)
        results = response.json()

        if "results" not in results:
            print(f"Error in Nearby Search: {results.get('status', 'Unknown error')}")
            break

        for place in results["results"]:
            transformed_result = {
                "id": place.get("place_id", ""),
                "types": place.get("types", []),
                "formattedAddress": place.get("vicinity", ""),
                "location": {
                    "latitude": place["geometry"]["location"]["lat"],
                    "longitude": place["geometry"]["location"]["lng"],
                },
                "rating": place.get("rating"),
                "userRatingCount": place.get("user_ratings_total"),
                "displayName": {
                    "text": place.get("name", ""),
                    "languageCode": "en",  # Assuming English, adjust if needed
                },
                "primaryType": place["types"][0] if place.get("types") else None,
            }
            all_results.append(transformed_result)

        next_page_token = results.get("next_page_token")
        if not next_page_token:
            break

    # Remove duplicates based on 'id'
    unique_results = {result["id"]: result for result in all_results}.values()

    return (
        list(unique_results),
        None,
    )  # Return None for next_page_token as we've fetched all pages


def calculate_distance_km(point1, point2):
    """
    Calculates the distance between two points in kilometers using the Haversine formula.

    """
    # Earth's radius in kilometers
    R = 6371

    # Convert latitude and longitude to radians
    lon1, lat1 = math.radians(point1[0]), math.radians(point1[1])
    lon2, lat2 = math.radians(point2[0]), math.radians(point2[1])

    # Differences in coordinates
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Haversine formula
    a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # Calculate the distance
    distance = R * c

    return distance


def generate_grid_points(
        center_lat: float, center_lng: float, radius_km: float, step_km: float = 0.1
) -> List[Tuple[float, float]]:
    """Generate a grid of points within the given radius."""
    points = []
    steps = int(radius_km / step_km)
    for i in range(-steps, steps + 1):
        for j in range(-steps, steps + 1):
            lat = center_lat + (
                    i * step_km / 111.32
            )  # 1 degree of latitude = 111.32 km
            lng = center_lng + (
                    j * step_km / (111.32 * math.cos(math.radians(center_lat)))
            )
            if calculate_distance_km((center_lng, center_lat), (lng, lat)) <= radius_km:
                points.append((lat, lng))
    return points


async def grid_fetch_from_google_maps_api(req: ReqLocation):
    lat, lng, radius, place_type = req.lat, req.lng, req.radius, req.type

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": CONF.api_key,
        "X-Goog-FieldMask": CONF.google_fields,
    }

    all_results = []
    grid_points = generate_grid_points(
        lat, lng, radius / 1000, 0.1
    )  # Convert radius to km

    for point_lat, point_lng in grid_points:
        data = {
            "includedTypes": [place_type],
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": point_lat, "longitude": point_lng},
                    "radius": 100,  # 100 meters
                }
            },
        }

        response = requests.post(CONF.nearby_search, headers=headers, json=data)
        if response.status_code == 200:
            response_data = response.json()
            results = response_data.get("places", [])
            all_results.extend(results)
        else:
            print(f"Error for point ({point_lat}, {point_lng}): {response.status_code}")

    # Remove duplicates based on 'id'
    unique_results = {result["id"]: result for result in all_results}.values()

    return (
        list(unique_results),
        None,
    )  # Return None for next_page_token as we're not using pagination


# Apply the decorator to all functions in this module
apply_decorator_to_module(logger)(__name__)
