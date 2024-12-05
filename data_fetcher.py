import logging
import math
import uuid
from typing import List, Dict, Any, Union, Tuple
import json
import orjson
from geopy.distance import geodesic
import numpy as np
from fastapi import HTTPException
from fastapi import status
import requests
from backend_common.auth import load_user_profile, update_user_profile
from config_factory import CONF
from all_types.myapi_dtypes import *
from all_types.response_dtypes import (
    ResGradientColorBasedOnZone,
    PrdcerLyrMapData,
    LayerInfo,
    UserCatalogInfo,
    NearestPointRouteResponse,
)
from google_api_connector import (
    calculate_distance_traffic_route,
    fetch_from_google_maps_api,
    text_fetch_from_google_maps_api,
)
from backend_common.logging_wrapper import (
    apply_decorator_to_module,
    preserve_validate_decorator,
)
from backend_common.logging_wrapper import log_and_validate
from mapbox_connector import MapBoxConnector
from storage import generate_layer_id
from storage import (
    store_data_resp,
    load_real_estate_categories,
    load_census_categories,
    get_real_estate_dataset_from_storage,
    get_census_dataset_from_storage,
    fetch_dataset_id,
    load_dataset,
    fetch_layer_owner,
    update_dataset_layer_matching,
    update_user_layer_matching,
    fetch_user_catalogs,
    load_user_layer_matching,
    fetch_user_layers,
    load_store_catalogs,
    convert_to_serializable,
    save_plan,
    get_plan,
    create_real_estate_plan,
    load_gradient_colors,
    make_dataset_filename,
)
from storage import (
    load_google_categories,
    load_country_city,
    make_include_exclude_name,
    make_ggl_layer_filename,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


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

    # Calculate the centers of the six outer circles
    outer_centers = []
    for i in range(6):
        angle = i * 60  # 360 degrees / 6 circles
        distance = radius * math.sqrt(3) / 2
        outer_center = get_point_at_distance(center, angle, distance)
        outer_centers.append(outer_center)

    # The center circle has the same center as the large circle
    all_centers = [center] + outer_centers

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


def print_circle_hierarchy(circle: dict, number=""):
    center_marker = "*" if circle["is_center"] else ""
    print(
        f"Circle {number}{center_marker}: Center: (lng: {circle['center'][0]:.4f}, lat: {circle['center'][1]:.4f}), Radius: {circle['radius']:.2f} km"
    )
    for i, sub_circle in enumerate(circle["sub_circles"], 1):
        print_circle_hierarchy(sub_circle, f"{number}.{i}" if number else f"{i}")


def count_circles(circle: dict):
    return 1 + sum(count_circles(sub_circle) for sub_circle in circle["sub_circles"])


# def create_string_list(circle_hierarchy, type_string, text_search):
#     result = []
#     circles_to_process = [circle_hierarchy]

#     while circles_to_process:
#         circle = circles_to_process.pop(0)

#         lat, lng = circle["center"]
#         radius = circle["radius"]

#         circle_string = f"{lat}_{lng}_{radius * 1000}_{type_string}"
#         if text_search != "" and text_search is not None:
#             circle_string = circle_string + f"_{text_search}"
#         result.append(circle_string)

#         circles_to_process.extend(circle.get("sub_circles", []))

#     return result


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

def to_location_req(req_dataset: Union[ReqCensus, ReqRealEstate, ReqLocation]) -> ReqLocation:
    # If it's already a ReqLocation, return it directly
    if isinstance(req_dataset, ReqLocation):
        return req_dataset
        
    # Load country/city data
    country_city_data = load_country_city()
    
    # Find the city coordinates
    city_data = None
    if req_dataset.country_name in country_city_data:
        for city in country_city_data[req_dataset.country_name]:
            if city["name"] == req_dataset.city_name:
                city_data = city
                break
    
    if not city_data:
        raise ValueError(f"City {req_dataset.city_name} not found in {req_dataset.country_name}")
    
    # Create ReqLocation object
    return ReqLocation(
        lat=city_data["lat"],
        lng=city_data["lng"],
        radius=5000,  # Default radius
        includedTypes=req_dataset.includedTypes,
        excludedTypes=[],  # Default empty list for excludedTypes
        page_token=req_dataset.page_token or ""
    )

async def fetch_census_realestate(
    req_dataset: Union[ReqCensus, ReqRealEstate], req_create_lyr: ReqFetchDataset, action: str = ''
) -> Tuple[Any, str, str, str]:
    next_page_token = req_dataset.page_token
    plan_name = ""
    bknd_dataset_id = ""

    if action == "full data":
        req_dataset, plan_name, next_page_token, current_plan_index, bknd_dataset_id = (
            await process_req_plan(req_dataset, req_create_lyr, action)
        )

    temp_req = to_location_req(req_dataset)
    bknd_dataset_id = make_dataset_filename(temp_req)
    dataset = await load_dataset(bknd_dataset_id)

    if not dataset:
        if isinstance(req_dataset, ReqCensus):
            get_dataset_func = get_census_dataset_from_storage
        elif isinstance(req_dataset, ReqRealEstate):
            get_dataset_func = get_real_estate_dataset_from_storage
        
        dataset, bknd_dataset_id = await get_dataset_func(
            req_dataset, bknd_dataset_id, action
        )
        if dataset:
            bknd_dataset_id = await store_data_resp(req_dataset, dataset, bknd_dataset_id)
    else:
        dataset = orjson.loads(dataset)

    return dataset, bknd_dataset_id, next_page_token, plan_name

# async def fetch_census_data(req_dataset: ReqCensus, req_create_lyr: ReqFetchDataset):
#     next_page_token = req_dataset.page_token
#     plan_name = ""
#     action = req_create_lyr.action
#     bknd_dataset_id = ""

#     if action == "full data":
#         req_dataset, plan_name, next_page_token, current_plan_index, bknd_dataset_id = (
#             await process_req_plan(req_dataset, req_create_lyr)
#         )
    
#     temp_req = to_location_req(req_dataset)
#     bknd_dataset_id = make_dataset_filename(temp_req)
#     dataset = await load_dataset(bknd_dataset_id)
#     if not dataset:
#         dataset, bknd_dataset_id = await get_census_dataset_from_storage(
#             req_dataset, bknd_dataset_id, action
#         )
#         if dataset:
#             bknd_dataset_id = await store_data_resp(req_dataset, dataset, bknd_dataset_id)
#     else:
#         dataset = orjson.loads(dataset)

#     return dataset, bknd_dataset_id, next_page_token, plan_name


# async def fetch_real_estate_nearby(
#     req_dataset: ReqRealEstate, req_create_lyr: ReqFetchDataset
# ):
#     next_page_token = req_dataset.page_token
#     plan_name = ""
#     action = req_create_lyr.action
#     bknd_dataset_id = ""

#     if action == "full data":
#         req_dataset, plan_name, next_page_token, current_plan_index, bknd_dataset_id = (
#             await process_req_plan(req_dataset, req_create_lyr)
#         )
#     temp_req = to_location_req(req_dataset)
#     bknd_dataset_id = make_dataset_filename(temp_req)
#     dataset = await load_dataset(bknd_dataset_id)
#     if not dataset:
#         dataset, bknd_dataset_id = await get_real_estate_dataset_from_storage(
#             req_dataset, bknd_dataset_id, action
#         )
#         if dataset:
#             bknd_dataset_id = await store_data_resp(req_dataset, dataset, bknd_dataset_id)
#     else:
#         dataset = orjson.loads(dataset)

#     return dataset, bknd_dataset_id, next_page_token, plan_name


async def fetch_ggl_nearby(req_dataset: ReqLocation, req_create_lyr: ReqFetchDataset, action: str = ''):
    search_type = req_create_lyr.search_type
    next_page_token = req_dataset.page_token
    plan_name = ""

    if action == "full data":
        req_dataset, plan_name, next_page_token, current_plan_index, bknd_dataset_id = (
            await process_req_plan(req_dataset, req_create_lyr, action)
        )
    temp_req = to_location_req(req_dataset)
    bknd_dataset_id = make_dataset_filename(temp_req)
    dataset = await load_dataset(bknd_dataset_id)
    if dataset:
        dataset = orjson.loads(dataset)
    # dataset, bknd_dataset_id = await get_dataset_from_storage(req_dataset)

    if not dataset:

        if "default" in search_type or "new nearby search" in search_type:
            dataset, _ = await fetch_from_google_maps_api(req_dataset)
        else:
            dataset, _ = await text_fetch_from_google_maps_api(req_dataset)

        if dataset:
            # Store the fetched data in storage
            dataset = await MapBoxConnector.new_ggl_to_boxmap(dataset)
            bknd_dataset_id = await store_data_resp(req_dataset, dataset, bknd_dataset_id)

    # if dataset is less than 20 or none and action is full data
    #     call function rectify plan
    #     replace next_page_token with next non-skip page token
    if len(dataset) < 20 and action == "full data":
        next_plan_index = await rectify_plan(plan_name, current_plan_index)
        if next_plan_index == "":
            next_page_token = ""
        else:
            next_page_token = (
                next_page_token.split("@#$")[0] + "@#$" + str(next_plan_index)
            )

    return dataset, bknd_dataset_id, next_page_token, plan_name


async def rectify_plan(plan_name, current_plan_index):
    plan = await get_plan(plan_name)
    rectified_plan = add_skip_to_subcircles(plan, current_plan_index)
    await save_plan(plan_name, rectified_plan)
    next_plan_index = get_next_non_skip_index(rectified_plan, current_plan_index)

    return next_plan_index


def get_next_non_skip_index(rectified_plan, current_plan_index):
    for i in range(current_plan_index + 1, len(rectified_plan)):
        if (
            not rectified_plan[i].endswith("_skip")
            and rectified_plan[i] != "end of search plan"
        ):
            # Return the new token with the found index
            return i

    # If no non-skipped item is found, return None or a special token
    return ""


def add_skip_to_subcircles(plan: list, token_plan_index: str):
    circle_string = plan[token_plan_index]
    # Extract the circle number from the input string

    circle_number = circle_string.split("_circle=")[1].split("_")[0].replace("*", "")

    def is_subcircle(circle):
        circle = "_circle=" + circle.split("_circle=")[1]
        return circle.startswith(f"_circle={circle_number}.")

    # Add "_skip" to subcircles
    modified_plan = []
    for circle in plan[:-1]:
        if is_subcircle(circle):
            if not circle.endswith("_skip"):
                circle += "_skip"
        modified_plan.append(circle)
    # Add the last item separately
    modified_plan.append(plan[-1])

    return modified_plan


async def process_req_plan(req_dataset, req_create_lyr, action: str = ''):
    plan: List[str] = []
    current_plan_index = 0
    bknd_dataset_id = ""

    if req_dataset.page_token == "" and action == "full data":

        if isinstance(req_dataset, ReqRealEstate):
            string_list_plan = await create_real_estate_plan(req_dataset)

        if isinstance(req_dataset, ReqLocation) and req_dataset.radius > 750:
            circle_hierarchy = cover_circle_with_seven_circles(
                (req_dataset.lng, req_dataset.lat), req_dataset.radius / 1000
            )
            type_string = make_include_exclude_name(
                req_dataset.includedTypes, req_dataset.excludedTypes
            )
            string_list_plan = create_string_list(
                circle_hierarchy, type_string, req_dataset.text_search
            )

        string_list_plan.append("end of search plan")

        # TODO creating the name of the file should be moved to storage
        tcc_string = make_ggl_layer_filename(req_create_lyr)
        plan_name = f"plan_{tcc_string}"
        if req_dataset.text_search != "" and req_dataset.text_search is not None:
            plan_name = plan_name + f"_text_search="
        await save_plan(plan_name, string_list_plan)
        plan = string_list_plan

        if isinstance(req_dataset, ReqLocation):
            next_search = string_list_plan[0]
            first_search = next_search.split("_")
            req_dataset.lng, req_dataset.lat, req_dataset.radius = (
                float(first_search[0]),
                float(first_search[1]),
                float(first_search[2]),
            )
        if isinstance(req_dataset, ReqRealEstate):
            bknd_dataset_id = plan[current_plan_index]
        next_page_token = f"page_token={plan_name}@#${1}"  # Start with the first search

    elif req_dataset.page_token != "":

        plan_name, current_plan_index = req_dataset.page_token.split("@#$")
        _, plan_name = plan_name.split("page_token=")
        current_plan_index = int(current_plan_index)
        plan = await get_plan(plan_name)

        if isinstance(req_dataset, ReqLocation):
            search_info = plan[current_plan_index].split("_")
            req_dataset.lng, req_dataset.lat, req_dataset.radius = (
                float(search_info[0]),
                float(search_info[1]),
                float(search_info[2]),
            )
            if plan[current_plan_index + 1] == "end of search plan":
                next_page_token = ""  # End of search plan
            else:
                next_page_token = f"page_token={plan_name}@#${current_plan_index + 1}"

        if isinstance(req_dataset, ReqRealEstate):

            next_plan_index = current_plan_index + 1
            bknd_dataset_id = plan[current_plan_index]
            if plan[current_plan_index + 1] == "end of search plan":
                next_page_token = ""  # End of search plan
            else:
                next_page_token = (
                    req_dataset.page_token.split("@#$")[0]
                    + "@#$"
                    + str(next_plan_index)
                )

    return req_dataset, plan_name, next_page_token, current_plan_index, bknd_dataset_id


async def fetch_catlog_collection():
    """
    Generates and returns a collection of catalog metadata. This function creates
    a list of predefined catalog entries and then adds 20 more dummy entries.
    Each entry contains information such as ID, name, description, thumbnail URL,
    and access permissions. This is likely used for testing or as placeholder data.
    """

    metadata = [
        {
            "id": "2",
            "name": "Saudi Arabia - Real Estate Transactions",
            "description": "Database of real-estate transactions in Saudi Arabia",
            "thumbnail_url": "https://catalog-assets.s3.ap-northeast-1.amazonaws.com/real_estate_ksa.png",
            "catalog_link": "https://example.com/catalog2.jpg",
            "records_number": 20,
            "can_access": True,
        },
        {
            "id": "55",
            "name": "Saudi Arabia - gas stations poi data",
            "description": "Database of all Saudi Arabia gas stations Points of Interests",
            "thumbnail_url": "https://catalog-assets.s3.ap-northeast-1.amazonaws.com/SAUgasStations.PNG",
            "catalog_link": "https://catalog-assets.s3.ap-northeast-1.amazonaws.com/SAUgasStations.PNG",
            "records_number": 8517,
            "can_access": False,
        },
        {
            "id": "65",
            "name": "Saudi Arabia - Restaurants, Cafes and Bakeries",
            "description": "Focusing on the restaurants, cafes and bakeries in KSA",
            "thumbnail_url": "https://catalog-assets.s3.ap-northeast-1.amazonaws.com/sau_bak_res.PNG",
            "catalog_link": "https://catalog-assets.s3.ap-northeast-1.amazonaws.com/sau_bak_res.PNG",
            "records_number": 132383,
            "can_access": False,
        },
    ]

    # Add 20 more dummy entries
    for i in range(3, 4):
        metadata.append(
            {
                "id": str(i),
                "name": f"Saudi Arabia - Sample Data {i}",
                "description": f"Sample description for dataset {i}",
                "thumbnail_url": "https://catalog-assets.s3.ap-northeast-1.amazonaws.com/sample_image.png",
                "catalog_link": "https://example.com/sample_image.jpg",
                "records_number": i * 100,
                "can_access": True,
            }
        )

    return metadata


async def fetch_layer_collection():
    """
    Similar to fetch_catlog_collection, this function returns a collection of layer
    metadata. It provides a smaller, fixed set of layer entries. Each entry includes
    details like ID, name, description, and access permissions.
    """

    metadata = [
        {
            "id": "2",
            "name": "Saudi Arabia - Real Estate Transactions",
            "description": "Database of real-estate transactions in Saudi Arabia",
            "thumbnail_url": "https://catalog-assets.s3.ap-northeast-1.amazonaws.com/real_estate_ksa.png",
            "catalog_link": "https://example.com/catalog2.jpg",
            "records_number": 20,
            "can_access": False,
        },
        {
            "id": "3",
            "name": "Saudi Arabia - 3",
            "description": "Database of all Saudi Arabia gas stations Points of Interests",
            "thumbnail_url": "https://catalog-assets.s3.ap-northeast-1.amazonaws.com/SAUgasStations.PNG",
            "catalog_link": "https://catalog-assets.s3.ap-northeast-1.amazonaws.com/SAUgasStations.PNG",
            "records_number": 8517,
            "can_access": False,
        },
    ]

    return metadata


async def fetch_country_city_data() -> Dict[str, List[Dict[str, float]]]:
    """
    Returns a set of country and city data for United Arab Emirates, Saudi Arabia, and Canada.
    The data is structured as a dictionary where keys are country names and values are lists of cities.
    """

    data = load_country_city()
    return data


async def validate_city_data(country, city):
    """Validates and returns city data"""
    country_city_data = await fetch_country_city_data()
    for c, cities in country_city_data.items():
        if c.lower() == country.lower():
            for city_data in cities:
                if city_data["name"].lower() == city.lower():
                    return city_data
    raise HTTPException(
        status_code=404, detail="City not found in the specified country"
    )


def determine_data_type(included_types: List[str], categories: Dict) -> Optional[str]:
    """
    Determines the data type based on included types by checking against all category types
    """
    if not included_types:
        return None

    for category_type, type_list in categories.items():
        # Handle both direct lists and nested dictionaries
        if isinstance(type_list, list):
            if set(included_types).intersection(set(type_list)):
                return category_type
        elif isinstance(type_list, dict):
            # Flatten nested categories for comparison
            all_subcategories = []
            for subcategories in type_list.values():
                if isinstance(subcategories, list):
                    all_subcategories.extend(subcategories)
            if set(included_types).intersection(set(all_subcategories)):
                return category_type

    return None


def prepare_response(dataset, bknd_dataset_id, next_page_token):
    """Prepares the final response"""
    return {
        "bknd_dataset_id": bknd_dataset_id,
        "records_count": len(dataset["features"]),
        "prdcer_lyr_id": generate_layer_id(),
        "next_page_token": next_page_token,
        **dataset,
    }


async def fetch_country_city_category_map_data(req: ReqFetchDataset, action: str = ''):
    """
    This function attempts to fetch an existing layer based on the provided
    request parameters. If the layer exists, it loads the data, transforms it,
    and returns it. If the layer doesn't exist, it creates a new layer by
    fetching data from Google Maps API.
    """
    next_page_token = None
    dataset_country = req.dataset_country
    dataset_city = req.dataset_city
    page_token = req.page_token
    text_search = req.text_search

    geojson_dataset = []

    # Fetch and validate city data
    city_data = await validate_city_data(dataset_country, dataset_city)

    # Load all categories
    categories = await fetch_nearby_categories()

    # Determine the data type based on included types
    data_type = determine_data_type(req.includedTypes, categories)

    if data_type == "real_estate":
        req_dataset = ReqRealEstate(
            country_name=req.dataset_country,
            city_name=req.dataset_city,
            excludedTypes=req.excludedTypes,
            includedTypes=req.includedTypes,
            page_token=req.page_token,
            text_search=req.text_search,
        )
        geojson_dataset, bknd_dataset_id, next_page_token, plan_name = (
            await fetch_census_realestate(req_dataset, req_create_lyr=req, action=action)
        )

    elif data_type in ["demographics", "economic", "housing", "social"]:
        req_dataset = ReqCensus(
            country_name=req.dataset_country,
            city_name=req.dataset_city,
            includedTypes=req.includedTypes,
            page_token=req.page_token,
        )
        geojson_dataset, bknd_dataset_id, next_page_token, plan_name = (
            await fetch_census_realestate(req_dataset, req_create_lyr=req, action=action)
        )

    else:
        # Default to Google Maps API
        req_dataset = ReqLocation(
            lat=city_data["lat"],
            lng=city_data["lng"],
            radius=30000,
            excludedTypes=req.excludedTypes,
            includedTypes=req.includedTypes,
            page_token=req.page_token,
            text_search=req.text_search,
        )
        geojson_dataset, bknd_dataset_id, next_page_token, plan_name = (
            await fetch_ggl_nearby(req_dataset, req_create_lyr=req, action=action)
        )

    # if request action was "full data" then store dataset id in the user profile
    # the name of the dataset will be the action + cct_layer name
    # make_ggl_layer_filename
    if action == "full data":
        user_data = await load_user_profile(req.user_id)
        user_data["prdcer"]["prdcer_dataset"][
            plan_name.replace("plan_", "")
        ] = plan_name
        await update_user_profile(req.user_id, user_data)

    geojson_dataset["bknd_dataset_id"] = bknd_dataset_id
    geojson_dataset["records_count"] = len(geojson_dataset["features"])
    geojson_dataset["prdcer_lyr_id"] = generate_layer_id()
    geojson_dataset["next_page_token"] = next_page_token
    return geojson_dataset


async def full_data_fetch_country_city_category_map_data(req: ReqFetchDataset):
    """
    Handle data fatch based on action
    """
    return await fetch_country_city_category_map_data(req, action="full data")


async def default_fetch_country_city_category_map_data(req: ReqFetchDataset):
    """
    Handle data fatch based on action
    """
    return await fetch_country_city_category_map_data(req)


async def save_lyr(req: ReqSavePrdcerLyer) -> str:
    user_data = await load_user_profile(req.user_id)

    try:
        # Add the new layer to user profile
        user_data["prdcer"]["prdcer_lyrs"][req.prdcer_lyr_id] = req.model_dump(
            exclude={"user_id"}
        )

        # Save updated user data
        await update_user_profile(req.user_id, user_data)
        await update_dataset_layer_matching(req.prdcer_lyr_id, req.bknd_dataset_id)
        await update_user_layer_matching(req.prdcer_lyr_id, req.user_id)
    except KeyError as ke:
        logger.error(f"Invalid user data structure for user_id: {req.user_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user data structure",
        ) from ke

    return "Producer layer created successfully"


@preserve_validate_decorator
@log_and_validate(logger, validate_output=True, output_model=List[LayerInfo])
async def aquire_user_lyrs(req: ReqUserId) -> List[LayerInfo]:
    """
    Retrieves all producer layers associated with a specific user. It reads the
    user's data file and the dataset-layer matching file to compile a list of
    all layers owned by the user, including metadata like layer name, color,
    and record count.
    """
    user_layers = await fetch_user_layers(req.user_id)

    user_layers_metadata = []
    for lyr_id, lyr_data in user_layers.items():
        try:
            dataset_id, dataset_info = await fetch_dataset_id(lyr_id)
            records_count = dataset_info["records_count"]

            user_layers_metadata.append(
                LayerInfo(
                    prdcer_lyr_id=lyr_id,
                    prdcer_layer_name=lyr_data["prdcer_layer_name"],
                    points_color=lyr_data["points_color"],
                    layer_legend=lyr_data["layer_legend"],
                    layer_description=lyr_data["layer_description"],
                    records_count=records_count,
                    is_zone_lyr="false",  # Default to "false" as string
                )
            )
        except KeyError as e:
            logger.error(f"Missing key in layer data: {str(e)}")
            # Continue to next layer instead of failing the entire request
            continue

    # if not user_layers_metadata:
    #     raise HTTPException(
    #         status_code=404, detail="No valid layers found for the user"
    #     )

    return user_layers_metadata


async def fetch_lyr_map_data(req: ReqPrdcerLyrMapData) -> PrdcerLyrMapData:
    """
    Fetches detailed map data for a specific producer layer.
    """
    try:
        user_layer_matching = await load_user_layer_matching()
        layer_owner_id = user_layer_matching.get(req.prdcer_lyr_id)
        layer_owner_data = await load_user_profile(layer_owner_id)

        try:
            layer_metadata = layer_owner_data["prdcer"]["prdcer_lyrs"][
                req.prdcer_lyr_id
            ]
        except KeyError as ke:
            raise HTTPException(
                status_code=404, detail="Producer layer not found for this user"
            ) from ke

        dataset_id, dataset_info = await fetch_dataset_id(req.prdcer_lyr_id)
        all_datasets = await load_dataset(dataset_id)
        if all_datasets:
            trans_dataset = orjson.loads(all_datasets)

        return PrdcerLyrMapData(
            type="FeatureCollection",
            features=trans_dataset["features"],
            prdcer_layer_name=layer_metadata["prdcer_layer_name"],
            prdcer_lyr_id=req.prdcer_lyr_id,
            bknd_dataset_id=dataset_id,
            points_color=layer_metadata["points_color"],
            layer_legend=layer_metadata["layer_legend"],
            layer_description=layer_metadata["layer_description"],
            records_count=dataset_info["records_count"],
            is_zone_lyr="false",
        )
    except HTTPException:
        raise


async def fetch_lyr_map_data_coordinates(
    req: ReqNearestRoute,
) -> List[NearestPointRouteResponse]:
    """
    Fetches detailed map data for a specific producer layer.
    """
    try:
        dataset_id, dataset_info = await fetch_dataset_id(req.prdcer_lyr_id)
        all_datasets = await load_dataset(dataset_id)
        coordinates_list = [
            {
                "latitude": item["location"]["latitude"],
                "longitude": item["location"]["longitude"],
            }
            for item in all_datasets
        ]

        business_target_coordinates = [
            {"latitude": point.latitude, "longitude": point.longitude}
            for point in req.points
        ]

        nearest_points = await calculate_nearest_points(
            coordinates_list, business_target_coordinates
        )

        Gmap_response = await calculate_nearest_points_Gmap(nearest_points)
        return Gmap_response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"An error occurred: {str(e)}"
        ) from e


async def calculate_nearest_points(
    category_coordinates: List[Dict[str, float]],
    bussiness_target_coordinates: List[Dict[str, float]],
) -> List[Dict[str, Any]]:
    nearest_locations = []
    for target in bussiness_target_coordinates:
        distances = []
        for loc in category_coordinates:
            dist = calculate_distance_km(
                (target["longitude"], target["latitude"]),
                (loc["longitude"], loc["latitude"]),
            )
            distances.append(
                {
                    "latitude": loc["latitude"],
                    "longitude": loc["longitude"],
                    "distance": dist,
                }
            )

        # Sort distances and get the nearest 3
        nearest = sorted(distances, key=lambda x: x["distance"])[:3]
        nearest_locations.append(
            {
                "target": target,
                "nearest_coordinates": [
                    (loc["latitude"], loc["longitude"]) for loc in nearest
                ],
            }
        )

    return nearest_locations


async def calculate_nearest_points_Gmap(
    nearest_locations: List[Dict[str, Any]]
) -> List[NearestPointRouteResponse]:
    results = []
    for item in nearest_locations:
        target = item["target"]
        target_routes = NearestPointRouteResponse(target=target, routes=[])

        for nearest in item["nearest_coordinates"]:
            origin = f"{target['latitude']},{target['longitude']}"
            destination = f"{nearest[0]},{nearest[1]}"

            try:
                # Fetch route information between target and nearest location
                route_info = await calculate_distance_traffic_route(origin, destination)
                target_routes.routes.append(route_info)
            except HTTPException as e:
                # Handle HTTP exceptions during the route fetching
                target_routes.routes.append({"error": str(e.detail)})
            except Exception as e:
                # Handle any other exceptions
                target_routes.routes.append({"error": f"An error occurred: {str(e)}"})

        results.append(target_routes)

    return results


async def create_save_prdcer_ctlg(req: ReqSavePrdcerCtlg) -> str:
    """
    Creates and saves a new producer catalog.
    """
    try:
        user_data = await load_user_profile(req.user_id)

        new_ctlg_id = str(uuid.uuid4())
        new_catalog = {
            "prdcer_ctlg_name": req.prdcer_ctlg_name,
            "prdcer_ctlg_id": new_ctlg_id,
            "subscription_price": req.subscription_price,
            "ctlg_description": req.ctlg_description,
            "total_records": req.total_records,
            "lyrs": req.lyrs,
            "thumbnail_url": req.thumbnail_url,
            "ctlg_owner_user_id": req.user_id,
        }
        user_data["prdcer"]["prdcer_ctlgs"][new_ctlg_id] = new_catalog

        serializable_user_data = convert_to_serializable(user_data)
        await update_user_profile(req.user_id, serializable_user_data)

        return new_ctlg_id
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while creating catalog: {str(e)}",
        ) from e


async def fetch_prdcer_ctlgs(req: ReqUserId) -> List[UserCatalogInfo]:
    """
    Retrieves all producer catalogs associated with a specific user.
    """
    try:
        user_catalogs = await fetch_user_catalogs(req.user_id)
        validated_catalogs = []

        for ctlg_id, ctlg_data in user_catalogs.items():
            validated_catalogs.append(
                UserCatalogInfo(
                    prdcer_ctlg_id=ctlg_id,
                    prdcer_ctlg_name=ctlg_data["prdcer_ctlg_name"],
                    ctlg_description=ctlg_data["ctlg_description"],
                    thumbnail_url=ctlg_data.get("thumbnail_url", ""),
                    subscription_price=ctlg_data["subscription_price"],
                    total_records=ctlg_data["total_records"],
                    lyrs=ctlg_data["lyrs"],
                    ctlg_owner_user_id=ctlg_data["ctlg_owner_user_id"],
                )
            )
        return validated_catalogs
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while fetching catalogs: {str(e)}",
        ) from e


async def fetch_ctlg_lyrs(req: ReqFetchCtlgLyrs) -> List[PrdcerLyrMapData]:
    """
    Fetches all layers associated with a specific catalog.
    """
    try:
        user_data = await load_user_profile(req.user_id)
        ctlg = (
            user_data.get("prdcer", {})
            .get("prdcer_ctlgs", {})
            .get(req.prdcer_ctlg_id, {})
        )

        if not ctlg:
            store_ctlgs = load_store_catalogs()
            ctlg = next(
                (
                    ctlg_info
                    for ctlg_key, ctlg_info in store_ctlgs.items()
                    if ctlg_key == req.prdcer_ctlg_id
                ),
                {},
            )

        if not ctlg:
            raise HTTPException(status_code=404, detail="Catalog not found")

        ctlg_owner_data = await load_user_profile(ctlg["ctlg_owner_user_id"])

        ctlg_lyrs_map_data = []
        for lyr_info in ctlg["lyrs"]:
            lyr_id = lyr_info["layer_id"]
            dataset_id, dataset_info = await fetch_dataset_id(lyr_id)
            dataset = await load_dataset(dataset_id)
            trans_dataset = await MapBoxConnector.new_ggl_to_boxmap(dataset)

            lyr_metadata = (
                ctlg_owner_data.get("prdcer", {}).get("prdcer_lyrs", {}).get(lyr_id, {})
            )

            ctlg_lyrs_map_data.append(
                PrdcerLyrMapData(
                    type="FeatureCollection",
                    features=trans_dataset["features"],
                    prdcer_layer_name=lyr_metadata.get(
                        "prdcer_layer_name", f"Layer {lyr_id}"
                    ),
                    prdcer_lyr_id=lyr_id,
                    bknd_dataset_id=dataset_id,
                    points_color=lyr_metadata.get("points_color", "red"),
                    layer_legend=lyr_metadata.get("layer_legend", ""),
                    layer_description=lyr_metadata.get("layer_description", ""),
                    records_count=len(trans_dataset["features"]),
                    is_zone_lyr="false",
                )
            )

        return ctlg_lyrs_map_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An error occurred: {str(e)}"
        ) from e


def calculate_thresholds(values: List[float]) -> List[float]:
    """
    Calculates threshold values to divide a set of values into three categories.
    """
    try:
        sorted_values = sorted(values)
        n = len(sorted_values)
        return [sorted_values[n // 3], sorted_values[2 * n // 3]]
    except Exception as e:
        raise ValueError(f"Error in calculate_thresholds: {str(e)}")


def calculate_distance_km(point1: List[float], point2: List[float]) -> float:
    """
    Calculates the distance between two points in kilometers using the Haversine formula.
    """
    try:
        R = 6371
        lon1, lat1 = math.radians(point1[0]), math.radians(point1[1])
        lon2, lat2 = math.radians(point2[0]), math.radians(point2[1])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c
        return distance
    except Exception as e:
        raise ValueError(f"Error in calculate_distance_km: {str(e)}")


# def create_feature(point: Dict[str, Any]) -> Feature:
#     """
#     Converts a point dictionary into a Feature object. This function is used
#     to ensure that all points are in the correct format for geospatial operations.
#     """
#     try:
#         return Feature(
#             type=point["type"],
#             properties=point["properties"],
#             geometry=Geometry(
#                 type="Point", coordinates=point["geometry"]["coordinates"]
#             ),
#         )
#     except KeyError as e:
#         raise ValueError(f"Invalid point data: missing key {str(e)}")
#     except Exception as e:
#         raise ValueError(f"Error creating feature: {str(e)}")


async def fetch_nearby_categories() -> Dict:
    """
    Provides a comprehensive list of place categories, including Google places,
    real estate, census data, and other custom categories.
    """
    google_categories = load_google_categories()
    real_estate_categories = await load_real_estate_categories()
    census_categories = await load_census_categories()
    # combine all category types
    categories = {**google_categories, **real_estate_categories, **census_categories}
    return categories


async def save_draft_catalog(req: ReqSavePrdcerLyer) -> str:
    try:
        user_data = await load_user_profile(req.user_id)
        if len(req.lyrs) > 0:

            new_ctlg_id = str(uuid.uuid4())
            new_catalog = {
                "prdcer_ctlg_name": req.prdcer_ctlg_name,
                "prdcer_ctlg_id": new_ctlg_id,
                "subscription_price": req.subscription_price,
                "ctlg_description": req.ctlg_description,
                "total_records": req.total_records,
                "lyrs": req.lyrs,
                "thumbnail_url": req.thumbnail_url,
                "ctlg_owner_user_id": req.user_id,
            }
            user_data["prdcer"]["draft_ctlgs"][new_ctlg_id] = new_catalog

            serializable_user_data = convert_to_serializable(user_data)
            await update_user_profile(req.user_id, serializable_user_data)

            return new_ctlg_id
        else:
            raise HTTPException(
                status_code=400,
                detail="No layers found in the request",
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while saving draft catalog: {str(e)}",
        ) from e


async def fetch_gradient_colors() -> List[List]:
    """ """

    data = await load_gradient_colors()
    return data


async def given_layer_fetch_dataset(layer_id: str):
    # given layer id get dataset
    user_layer_matching = await load_user_layer_matching()
    layer_owner_id = user_layer_matching.get(layer_id)
    layer_owner_data = await load_user_profile(layer_owner_id)
    try:
        layer_metadata = layer_owner_data["prdcer"]["prdcer_lyrs"][layer_id]
    except KeyError as ke:
        raise HTTPException(
            status_code=404, detail="Producer layer not found for this user"
        ) from ke

    dataset_id, dataset_info = await fetch_dataset_id(layer_id)
    all_datasets = await load_dataset(dataset_id)

    return all_datasets


async def gradient_color_based_on_zone(
    req: ReqGradientColorBasedOnZone,
) -> List[ResGradientColorBasedOnZone]:
    change_layer_dataset = await given_layer_fetch_dataset(req.change_lyr_id)
    based_on_layer_dataset = await given_layer_fetch_dataset(req.based_on_lyr_id)

    def calculate_distance(lat1, lon1, lat2, lon2):
        return geodesic((lat1, lon1), (lat2, lon2)).meters

    def get_nearby_average_metric(color_based_on, point, based_on_dataset, radius):
        lat, lon = point["location"]["latitude"], point["location"]["longitude"]
        nearby_metric_value = [
            p[color_based_on]
            for p in based_on_dataset
            if color_based_on in p
            and calculate_distance(
                lat, lon, p["location"]["latitude"], p["location"]["longitude"]
            )
            <= radius
        ]
        return np.mean(nearby_metric_value) if nearby_metric_value else None

    # Calculate influence scores for change_layer_dataset and store them
    influence_scores = []
    point_influence_map = {}
    for point in change_layer_dataset:
        avg_metric = get_nearby_average_metric(
            req.color_based_on, point, based_on_layer_dataset, req.radius_offset
        )
        if avg_metric is not None:
            influence_scores.append(avg_metric)
            point_influence_map[point["id"]] = avg_metric

    # Calculate thresholds based on influence scores
    percentiles = [16.67, 33.33, 50, 66.67, 83.33]
    thresholds = np.percentile(influence_scores, percentiles)

    # Create layers
    new_layers = []
    layer_data = [
        [] for _ in range(len(thresholds) + 2)
    ]  # +1 for above highest threshold, +1 for unallocated

    # Assign points to layers
    for point in change_layer_dataset:
        avg_metric = point_influence_map.get(point["id"])
        feature = MapBoxConnector.assign_point_properties(point)

        if avg_metric is None:
            layer_index = -1  # Last layer (unallocated)
            feature["properties"]["influence_score"] = None
        else:
            layer_index = next(
                (
                    i
                    for i, threshold in enumerate(thresholds)
                    if avg_metric <= threshold
                ),
                len(thresholds),
            )
            feature["properties"]["influence_score"] = avg_metric

        layer_data[layer_index].append(feature)

    # Create layers only for non-empty data
    for i, data in enumerate(layer_data):
        if data:
            color = (
                req.color_grid_choice[i] if i < len(req.color_grid_choice) else "white"
            )
            if i == len(layer_data) - 1:
                layer_name = "Unallocated Points"
                layer_legend = "No nearby points"
            elif i == 0:
                layer_name = f"Gradient Layer {i+1}"
                layer_legend = f"Influence Score < {thresholds[0]:.2f}"
            elif i == len(thresholds):
                layer_name = f"Gradient Layer {i+1}"
                layer_legend = f"Influence Score > {thresholds[-1]:.2f}"
            else:
                layer_name = f"Gradient Layer {i+1}"
                layer_legend = (
                    f"Influence Score {thresholds[i-1]:.2f} - {thresholds[i]:.2f}"
                )

            new_layers.append(
                ResGradientColorBasedOnZone(
                    type="FeatureCollection",
                    features=data,
                    prdcer_layer_name=layer_name,
                    prdcer_lyr_id=req.change_lyr_id,
                    sub_lyr_id=f"{req.change_lyr_id}_gradient_{i+1}",
                    bknd_dataset_id=req.change_lyr_id,
                    points_color=color,
                    layer_legend=layer_legend,
                    layer_description=f"Gradient layer based on nearby {req.color_based_on} influence",
                    records_count=len(data),
                    is_zone_lyr="true",
                )
            )

    return new_layers


async def get_user_profile(req):
    return await load_user_profile(req.user_id)


# Apply the decorator to all functions in this module
apply_decorator_to_module(logger)(__name__)
