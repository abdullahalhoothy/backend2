import math
from geopy.distance import geodesic
import geopy.distance
from datetime import timedelta, datetime
import logging
from typing import Optional, Dict, Any, List, Tuple
from geopy.geocoders import Nominatim
from all_types.request_dtypes import ReqFetchDataset, ReqGeodata
from constants import load_country_city

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_point_at_distance(start_point, bearing, distance_km):
    return geodesic(kilometers=distance_km).destination(start_point, bearing)


def calculate_distance(coord1, coord2):
    """
    Calculate the distance between two points (latitude and longitude) in meters.
    """
    return geopy.distance.distance(
        (coord1["latitude"], coord1["longitude"]),
        (coord2["latitude"], coord2["longitude"]),
    ).meters


EXPANSION_DISTANCE_KM = (
    60.0  # for each side from the center of the bounding box
)


def expand_bounding_box(
    lat: float, lon: float, expansion_distance_km: float = EXPANSION_DISTANCE_KM
) -> list:
    try:
        center_point = (lat, lon)

        # Calculate the distance in degrees
        north_expansion = geodesic(
            kilometers=expansion_distance_km
        ).destination(
            center_point, 0
        )  # North
        south_expansion = geodesic(
            kilometers=expansion_distance_km
        ).destination(
            center_point, 180
        )  # South
        east_expansion = geodesic(kilometers=expansion_distance_km).destination(
            center_point, 90
        )  # East
        west_expansion = geodesic(kilometers=expansion_distance_km).destination(
            center_point, 270
        )  # West

        expanded_bbox = [
            south_expansion[0],
            north_expansion[0],
            west_expansion[1],
            east_expansion[1],
        ]

        return expanded_bbox
    except Exception as e:
        logger.error(f"Error expanding bounding box: {str(e)}")
        return None


# Global cache dictionary to store previously fetched locations
_LOCATION_CACHE = {}


def get_req_geodata(city_name: str, country_name: str) -> Optional[ReqGeodata]:
    # Create cache key
    cache_key = f"{city_name},{country_name}"

    # Check if result exists in cache
    if cache_key in _LOCATION_CACHE:
        return _LOCATION_CACHE[cache_key]

    try:
        geolocator = Nominatim(user_agent="city_country_search")
        location = geolocator.geocode(f"{city_name}, {country_name}", exactly_one=True)

        if not location:
            logger.warning(f"No location found for {city_name}, {country_name}")
            _LOCATION_CACHE[cache_key] = None
            return None

        bounding_box = expand_bounding_box(location.latitude, location.longitude)
        if bounding_box is None:
            logger.warning(f"No bounding box found for {city_name}, {country_name}")
            _LOCATION_CACHE[cache_key] = None
            return None

        result = ReqGeodata(
            lat=float(location.latitude),
            lng=float(location.longitude),
            bounding_box=bounding_box,
        )

        # Store in cache before returning
        _LOCATION_CACHE[cache_key] = result
        return result

    except Exception as e:
        logger.error(f"Error getting geodata for {city_name}, {country_name}: {str(e)}")
        _LOCATION_CACHE[cache_key] = None
        return None


def fetch_lat_lng_bounding_box(req: ReqFetchDataset) -> ReqFetchDataset:
    # If lat and lng are provided directly, use them
    if req.lat is not None and req.lng is not None:
        req._bounding_box = expand_bounding_box(req.lat, req.lng)
        return req

    # Load country/city data
    country_city_data = load_country_city()

    # Find the city coordinates
    city_data = None

    if not req.city_name:
        raise ValueError(
            "Either city_name or lat/lng coordinates must be provided"
        )

    if req.country_name in country_city_data:
        for city in country_city_data[req.country_name]:
            if city["name"] == req.city_name:
                if (
                    city.get("lat") is None
                    or city.get("lng") is None
                    or city.get("bounding_box") is None
                ):
                    raise ValueError(
                        f"Invalid city data for {req.city_name} in {req.country_name}"
                    )
                req._bounding_box = expand_bounding_box(
                    city.get("lat"), city.get("lng")
                )
                req.lat = city.get("lat")
                req.lng = city.get("lng")
    else:
        # if city not found in country_city_data, use geocoding to get city_data
        city_data = get_req_geodata(req.city_name, req.country_name)
        req._bounding_box = city_data.bounding_box
        req.lat = city_data.lat
        req.lng = city_data.lng

    return req


def cover_circle_with_seven_circles_helper(center, radius_km):
    distance = radius_km * math.sqrt(3) / 2

    outer_centers = []
    for i in range(6):
        angle = i * 60  # 6 circles around at equal angles
        outer_center = get_point_at_distance(center[::-1], angle, distance)
        outer_centers.append((outer_center.longitude, outer_center.latitude))

    return [center] + outer_centers
