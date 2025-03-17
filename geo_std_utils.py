import math
<<<<<<< HEAD


def get_point_at_distance(start_point: tuple, bearing: float, distance: float):
    """
    Calculate the latitude and longitude of a point at a given distance and bearing from a start point.
    """
    R = 6371  # Earth's radius in km
    lat1 = math.radians(start_point[1])
    lon1 = math.radians(start_point[0])
    bearing = math.radians(bearing)

    lat2 = math.asin(
        math.sin(lat1) * math.cos(distance / R)
        + math.cos(lat1) * math.sin(distance / R) * math.cos(bearing)
    )
    lon2 = lon1 + math.atan2(
        math.sin(bearing) * math.sin(distance / R) * math.cos(lat1),
        math.cos(distance / R) - math.sin(lat1) * math.sin(lat2),
    )

    return (math.degrees(lon2), math.degrees(lat2))
=======
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
>>>>>>> 5969bd781b948b4e694a8f066317b2c2dc7c303c
