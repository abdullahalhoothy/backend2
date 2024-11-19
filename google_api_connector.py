import aiohttp
import logging
import math
from typing import List, Tuple, Dict

from fastapi import HTTPException
import requests

from all_types.myapi_dtypes import ReqLocation, ReqStreeViewCheck
from config_factory import CONF
from backend_common.logging_wrapper import apply_decorator_to_module
from all_types.response_dtypes import (
    LegInfo,
    TrafficCondition,
    RouteInfo,
)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)





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

        return results, ""
    else:
        print("Error:", response.status_code)
        return [], None


async def text_fetch_from_google_maps_api(req: ReqLocation):


    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": CONF.api_key,
        "X-Goog-FieldMask": CONF.google_fields,
    }
    data = {
        "textQuery": req.text_search,
    }

    response = requests.post(CONF.search_text, headers=headers, json=data)
    if response.status_code == 200:
        response_data = response.json()
        results = response_data.get("places", [])

        return results, ""
    else:
        print("Error:", response.status_code)
        return [], None


async def check_street_view_availability(req: ReqStreeViewCheck) -> Dict[str, bool]:
    url = f"https://maps.googleapis.com/maps/api/streetview?return_error_code=true&size=600x300&location={req.lat},{req.lng}&heading=151.78&pitch=-0.76&key={CONF.api_key}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return {"has_street_view": True}
            else:
                raise HTTPException(
                    status_code=response.status,
                    detail="Error checking Street View availability",
                )
async def calculate_distance_traffic_route(origin: str, destination: str) -> RouteInfo: #GoogleApi connector
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"

    payload = {
        "origin": {"location": {"latLng": {"latitude": origin.split(",")[0], "longitude": origin.split(",")[1]}}},
        "destination": {"location": {"latLng": {"latitude": destination.split(",")[0], "longitude": destination.split(",")[1]}}},
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
        "computeAlternativeRoutes": True,
        "extraComputations": ["TRAFFIC_ON_POLYLINE"],
        "polylineQuality": "high_quality",
    }

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": CONF.api_key,
        "X-Goog-fieldmask": "*"
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
                        speed=interval["speed"]
                    )
                    for interval in leg["travelAdvisory"].get("speedReadingIntervals", [])
                ]
            )
            route_info.append(leg_info)

        return RouteInfo(
            origin=origin,
            destination=destination,
            route=route_info
        )

    except requests.RequestException:
        raise HTTPException(status_code=400, detail="Error fetching route information from Google Maps API")

# Apply the decorator to all functions in this module
apply_decorator_to_module(logger)(__name__)
