import math
from geopy.distance import geodesic
import geopy.distance


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