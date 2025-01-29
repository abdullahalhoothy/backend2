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
from config_factory import CONF
from backend_common.logging_wrapper import apply_decorator_to_module
from all_types.response_dtypes import (
    LegInfo,
    TrafficCondition,
    RouteInfo,
)
from boolean_query_processor import optimize_query_sequence,test_optimized_queries

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
        optimized_queries = optimize_query_sequence(req.boolean_query, POPULARITY_DATA)

        query_tasks = [
            execute_single_query(req, included_types, excluded_types)
            for included_types, excluded_types in optimized_queries
        ]

        logger.info(f"Executing {len(optimized_queries)} parallel queries")
        all_query_results = await asyncio.gather(*query_tasks)

        seen_places = set()
        all_results = []

        # Log results for each query
        for i, (results, (included, excluded)) in enumerate(
            zip(all_query_results, optimized_queries)
        ):
            new_results = [r for r in results if r["id"] not in seen_places]
            logger.info(f"Query {i} results - Include: {included}, Exclude: {excluded}")
            logger.info(
                f"  Found {len(results)} total places, {len(new_results)} new places"
            )
            seen_places.update(r["id"] for r in new_results)
            all_results.extend(new_results)

        logger.info(f"Total unique places found: {len(all_results)}")
        return all_results, ""

    except Exception as e:
        # TODO this doesn't reraise the error, not sure what to do about it
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
