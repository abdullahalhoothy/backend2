import aiohttp
import logging
import math
from typing import List, Dict, Any, Tuple, Optional
import pyparsing as pp  # Library for parsing text/expressions
from dataclasses import dataclass
import json
import asyncio
from fastapi import HTTPException
import requests
from sympy import Symbol
from typing import Dict, Set, List
from all_types.myapi_dtypes import ReqLocation, ReqStreeViewCheck
from backend_common.utils.utils import convert_strings_to_ints
from config_factory import CONF
from backend_common.logging_wrapper import apply_decorator_to_module
from all_types.response_dtypes import (
    LegInfo,
    TrafficCondition,
    RouteInfo,
)
from boolean_query_processor import optimize_query_sequence,test_optimized_queries
from mapbox_connector import MapBoxConnector
from storage import load_dataset, make_dataset_filename, make_dataset_filename_part, store_data_resp
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# async def fetch_from_google_maps_api(req: ReqLocation):

#     headers = {
#         "Content-Type": "application/json",
#         "X-Goog-Api-Key": CONF.api_key,
#         "X-Goog-FieldMask": CONF.google_fields,
#     }
#     data = {
#         "included_types": [req.included_types],
#         "excludedTypes": [req.excludedTypes],
#         "locationRestriction": {
#             "circle": {
#                 "center": {"latitude": req.lat, "longitude": req.lng},
#                 "radius": req.radius,
#             }
#         },
#     }

#     response = requests.post(CONF.nearby_search, headers=headers, json=data)
#     if response.status_code == 200:
#         response_data = response.json()
#         results = response_data.get("places", [])

#         return results, ""
#     else:
#         print("Error:", response.status_code)
#         return [], None


# Load and flatten the popularity data
with open("Backend/ggl_categories_poi_estimate.json", "r") as f:
    raw_popularity_data = json.load(f)

# Flatten the nested dictionary - we only care about subkeys
POPULARITY_DATA = {}
for category in raw_popularity_data.values():
    POPULARITY_DATA.update(category)


async def fetch_from_google_maps_api(req: ReqLocation) -> Tuple[List[Dict[str, Any]], str]:
    try:

        combined_dataset_id = make_dataset_filename(req)
        existing_combined_data = await load_dataset(combined_dataset_id)
        
        if existing_combined_data:
            logger.info(f"Returning existing combined dataset: {combined_dataset_id}")
            return existing_combined_data
        optimized_queries = optimize_query_sequence(req.boolean_query, POPULARITY_DATA)

        datasets = {}
        missing_queries = []
        seen_places = set() 

        for included_types, excluded_types in optimized_queries:
            full_dataset_id = make_dataset_filename_part(req, included_types, excluded_types)
            stored_data = await load_dataset(full_dataset_id)

            if stored_data:
                datasets[full_dataset_id] = stored_data
            else:
                missing_queries.append((full_dataset_id, included_types, excluded_types))

        if not missing_queries:
            all_results = [
                place for dataset in datasets.values() if isinstance(dataset, list) for place in dataset
            ]
            return all_results

        logger.info(f"Fetching {len(missing_queries)} queries from Google Maps API.")
        query_tasks = [
            execute_single_query(req, included_types, excluded_types)
            for _, included_types, excluded_types in missing_queries
        ]

        all_query_results = await asyncio.gather(*query_tasks)

        for (dataset_id, included, excluded), query_results in zip(missing_queries, all_query_results):
            if query_results:
                new_results = [place for place in query_results if place.get("place_id","") not in seen_places]
                
                if new_results:  
                    dataset = await MapBoxConnector.new_ggl_to_boxmap(new_results,req.radius)
                    dataset = convert_strings_to_ints(dataset)
                    await store_data_resp(req, dataset, dataset_id)
                    datasets[dataset_id] = new_results
                    for place in new_results:
                        seen_places.add(place.get("place_id"))

        all_results = []
        for dataset in datasets.values():
            if isinstance(dataset, list):
                for place in dataset:
                    if isinstance(place, dict):
                        all_results.append(place)

        if all_results:
            dataset = await MapBoxConnector.new_ggl_to_boxmap(all_results,req.radius)
            dataset = convert_strings_to_ints(dataset)
            await store_data_resp(req, dataset, combined_dataset_id)
            logger.info(f"Stored combined dataset: {combined_dataset_id}")
            logger.info(f"Fetched {len(dataset)} places from Google Maps API and DB.")
            return dataset
        else:
            logger.warning("No valid results returned from Google Maps API or DB.")
            return [], "No valid results from API or DB"

    except Exception as e:
        logger.error(f"Error in fetch_from_google_maps_api: {str(e)}")
        return [], str(e)


async def execute_single_query(
    location_data: ReqLocation, included_types: List[str], excluded_types: List[str]
) -> List[dict]:
    data = {
        "includedTypes": included_types,
        "excludedTypes": excluded_types,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": location_data.lat,
                    "longitude": location_data.lng,
                },
                "radius": location_data.radius,
            }
        },
    }

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": CONF.api_key,
        "X-Goog-FieldMask": CONF.google_fields,
    }

    try:
        async with aiohttp.ClientSession() as session:
            logger.debug(
                f"Executing query - Include: {included_types}, Exclude: {excluded_types}"
            )
            async with session.post(
                CONF.nearby_search, headers=headers, json=data
            ) as response:
                if response.status == 200:
                    response_data = await response.json()
                    results = response_data.get("places", [])
                    logger.debug(f"Query returned {len(results)} results")
                    return results
                else:
                    error_msg = await response.text()
                    logger.error(f"API request failed: {error_msg}")
                    return []

    except aiohttp.ClientError as e:
        # TODO this doesn't reraise the error, not sure what to do about it
        logger.error(f"Network error during API request: {str(e)}")
        return []





async def text_fetch_from_google_maps_api(req: ReqLocation) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": CONF.api_key,
        "X-Goog-FieldMask": CONF.google_fields,
    }
    data = {
        "textQuery": req.text_search,
        "includePureServiceAreaBusinesses": False,
        "pageToken": req.page_token,
        "locationBias": {
            "circle": {
                "center": {"latitude": req.lat, "longitude": req.lng},
                "radius": req.radius,
            }
        },
    }
    response = requests.post(CONF.search_text, headers=headers, json=data)
    if response.status_code == 200:
        response_data = response.json()
        results = response_data.get("places", [])
        next_page_token = response_data.get("nextPageToken", "")
        return results, next_page_token
    else:
        print("Error:", response.status_code, response.text)
        return [], None


async def check_street_view_availability(req: ReqStreeViewCheck) -> Dict[str, bool]:
    url = f"https://maps.googleapis.com/maps/api/streetview?return_error_code=true&size=600x300&location={req.lat},{req.lng}&heading=151.78&pitch=-0.76&key={CONF.api_key}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return {"has_street_view": True}
            else:
                raise HTTPException(
                    status_code=499,
                    detail=f"Error checking Street View availability, error = {response.status}",
                )


async def calculate_distance_traffic_route(
    origin: str, destination: str
) -> RouteInfo:  # GoogleApi connector
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"

    payload = {
        "origin": {
            "location": {
                "latLng": {
                    "latitude": origin.split(",")[0],
                    "longitude": origin.split(",")[1],
                }
            }
        },
        "destination": {
            "location": {
                "latLng": {
                    "latitude": destination.split(",")[0],
                    "longitude": destination.split(",")[1],
                }
            }
        },
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
        "computeAlternativeRoutes": True,
        "extraComputations": ["TRAFFIC_ON_POLYLINE"],
        "polylineQuality": "high_quality",
    }

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": CONF.api_key,
        "X-Goog-fieldmask": "*",
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()

        if "routes" not in response_data:
            raise HTTPException(status_code=400, detail="No route found.")

        # Parse the first route's leg for necessary details
        route_info = []
        for leg in response_data["routes"][0]["legs"]:
            leg_info = LegInfo(
                start_location=leg["startLocation"],
                end_location=leg["endLocation"],
                distance=leg["distanceMeters"],
                duration=leg["duration"],
                static_duration=leg["staticDuration"],
                polyline=leg["polyline"]["encodedPolyline"],
                traffic_conditions=[
                    TrafficCondition(
                        start_index=interval.get("startPolylinePointIndex", 0),
                        end_index=interval["endPolylinePointIndex"],
                        speed=interval["speed"],
                    )
                    for interval in leg["travelAdvisory"].get(
                        "speedReadingIntervals", []
                    )
                ],
            )
            route_info.append(leg_info)

        return RouteInfo(origin=origin, destination=destination, route=route_info)

    except requests.RequestException:
        raise HTTPException(
            status_code=400,
            detail="Error fetching route information from Google Maps API",
        )


# Apply the decorator to all functions in this module
apply_decorator_to_module(logger)(__name__)
