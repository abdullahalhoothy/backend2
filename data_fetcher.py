import logging
import math
import uuid
from typing import List, Dict, Any
import json

import numpy as np
from fastapi import HTTPException
from fastapi import status

from all_types.myapi_dtypes import ReqLocation,ReqRealEstate
from all_types.myapi_dtypes import (
    ReqSavePrdcerLyer,
    ReqUserId,
    ReqSavePrdcerCtlg,
    ReqFetchCtlgLyrs,
    ReqApplyZoneLayers,
    ReqPrdcerLyrMapData,
    ReqFetchDataset,
)
from all_types.response_dtypes import (
    Geometry,
    Feature,
    LayerInfo,
    PrdcerLyrMapData,
    UserCatalogInfo,
)
from google_api_connector import fetch_from_google_maps_api
from logging_wrapper import apply_decorator_to_module, preserve_validate_decorator
from logging_wrapper import log_and_validate
from mapbox_connector import MapBoxConnector
from storage import generate_layer_id
from storage import (
    get_dataset_from_storage,
    store_ggl_data_resp,
    load_real_estate_categories,
    get_real_estate_dataset_from_storage,
    fetch_dataset_id,
    load_dataset,
    fetch_layer_owner,
    load_user_profile,
    update_dataset_layer_matching,
    update_user_layer_matching,
    fetch_user_catalogs,
    update_user_profile,
    load_dataset_layer_matching,
    fetch_user_layers,
    load_store_catalogs,
    convert_to_serializable,
    save_plan,
    get_plan,
    get_real_estate_folder
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

async def fetch_real_estate_nearby(req_dataset: ReqRealEstate, req_create_lyr: ReqFetchDataset):
    next_page_token = req_dataset.page_token
    plan_name = ""

    if req_create_lyr.action == "full data":
        req_dataset, plan_name, next_page_token, current_plan_index = await process_real_estate_req_plan(
            req_dataset, req_create_lyr
        )

        plan_data=await get_plan(plan_name)
        bknd_dataset_id=plan_data[current_plan_index]

        dataset, bknd_dataset_id = await get_real_estate_dataset_from_storage(req_dataset, bknd_dataset_id)    
        next_plan_index =current_plan_index+1
        if next_page_token=='' :
            next_page_token=""
        else:
            next_page_token = next_page_token.split('@#$')[0]+'@#$'+str(next_plan_index)




    return dataset, bknd_dataset_id, next_page_token, plan_name



async def fetch_ggl_nearby(req_dataset: ReqLocation, req_create_lyr: ReqFetchDataset):
    search_type = req_create_lyr.search_type
    next_page_token = req_dataset.page_token
    plan_name = ""

    if req_create_lyr.action == "full data":
        req_dataset, plan_name, next_page_token, current_plan_index = await process_req_plan(
            req_dataset, req_create_lyr
        )

    dataset, bknd_dataset_id = await get_dataset_from_storage(req_dataset)

    if not dataset:

        if "default" in search_type or "new nearby search" in search_type:
            dataset, _ = await fetch_from_google_maps_api(req_dataset)
        # elif "default" in search_type or "old nearby search" in search_type:
        #     dataset, next_page_token = await old_fetch_from_google_maps_api(req_dataset)
        # elif 'nearby but actually text search' in search_type:
        #     dataset, next_page_token = await text_as_nearby_fetch_from_google_maps_api(req)
        # else:  # text search
        #     dataset, next_page_token = await text_fetch_from_google_maps_api(req)

        if dataset is not None:
            # Store the fetched data in storage
            bknd_dataset_id = await store_ggl_data_resp(req_dataset, dataset)

    # if dataset is less than 20 or none and action is full data
    #     call function rectify plan
    #     replace next_page_token with next non-skip page token
    if len(dataset) < 20 and req_create_lyr.action == "full data":
        next_plan_index = await rectify_plan(plan_name, current_plan_index)
        if next_plan_index=="":
            next_page_token=""
        else:
            next_page_token = next_page_token.split('@#$')[0]+'@#$'+str(next_plan_index)




    return dataset, bknd_dataset_id, next_page_token, plan_name


async def rectify_plan(plan_name, current_plan_index):
    plan = await get_plan(plan_name)
    rectified_plan = add_skip_to_subcircles(plan, current_plan_index)
    await save_plan(plan_name, rectified_plan)
    next_plan_index= get_next_non_skip_index(rectified_plan, current_plan_index)

    return next_plan_index


def get_next_non_skip_index(rectified_plan, current_plan_index):
    for i in range(current_plan_index + 1, len(rectified_plan)):
        if not rectified_plan[i].endswith('_skip') and rectified_plan[i]!="end of search plan":
            # Return the new token with the found index
            return i
    
    # If no non-skipped item is found, return None or a special token
    return ""

def add_skip_to_subcircles(plan:list, token_plan_index:str):
    circle_string= plan[token_plan_index]
    # Extract the circle number from the input string

    circle_number = circle_string.split("_circle=")[1].split("_")[0].replace("*","")

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



async def process_req_plan(req_dataset, req_create_lyr):
    action = req_create_lyr.action
    plan: List[str] = []
    current_plan_index = 0

    if (
        req_dataset.radius > 750
        and req_dataset.page_token == ""
        and action == "full data"
    ):
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
            plan_name = plan_name + f"_text_search:"
        await save_plan(plan_name, string_list_plan)
        next_search = string_list_plan[0]
        first_search = next_search.split("_")
        req_dataset.lng, req_dataset.lat, req_dataset.radius = (
            float(first_search[0]),
            float(first_search[1]),
            float(first_search[2]),
        )
        next_page_token = f"page_token={plan_name}@#${1}"  # Start with the first search

    elif req_dataset.page_token != "":
        plan_name, current_plan_index = req_dataset.page_token.split("@#$")
        _, plan_name = plan_name.split("page_token=")
        current_plan_index = int(current_plan_index)
        plan = await get_plan(plan_name)
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


    return req_dataset, plan_name, next_page_token, current_plan_index


async def process_real_estate_req_plan(req_dataset, req_create_lyr):
    action = req_create_lyr.action
    plan: List[str] = []
    current_plan_index = 0

    if (
        req_dataset.page_token == ""
        and action == "full data"
    ):
        
        string_list_plan=await get_real_estate_folder(req_dataset)
        
        string_list_plan.append("end of search plan")

        # TODO creating the name of the file should be moved to storage
        tcc_string = make_ggl_layer_filename(req_create_lyr)
        plan_name = f"plan_{tcc_string}"
        if req_dataset.text_search != "" and req_dataset.text_search is not None:
            plan_name = plan_name + f"_text_search:"
        await save_plan(plan_name, string_list_plan)
        next_page_token = f"page_token={plan_name}@#${1}"  # Start with the first search

    elif req_dataset.page_token != "":
        plan_name, current_plan_index = req_dataset.page_token.split("@#$")
        _, plan_name = plan_name.split("page_token=")
        current_plan_index = int(current_plan_index)
        plan = await get_plan(plan_name)
        
        if plan[current_plan_index + 1] == "end of search plan":
            next_page_token = ""  # End of search plan
        else:
            next_page_token = f"page_token={plan_name}@#${current_plan_index + 1}"


    return req_dataset, plan_name, next_page_token, current_plan_index



async def fetch_catlog_collection(**_):
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


async def fetch_layer_collection(**_):
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


async def fetch_country_city_data(
    req: ReqFetchDataset,
) -> Dict[str, List[Dict[str, float]]]:
    """
    Returns a set of country and city data for United Arab Emirates, Saudi Arabia, and Canada.
    The data is structured as a dictionary where keys are country names and values are lists of cities.
    """

    data = load_country_city()
    return data


async def fetch_country_city_category_map_data(req: ReqFetchDataset):
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

    existing_dataset = []
    # Fetch country and city data
    country_city_data = await fetch_country_city_data("")

    # Find the city data
    city_data = None
    for country, cities in country_city_data.items():
        if country == dataset_country:
            for city in cities:
                if city["name"] == dataset_city:
                    city_data = city
                    break
            if city_data:
                break

    if not city_data:
        raise HTTPException(
            status_code=404, detail="City not found in the specified country"
        )
    
    #TODO fix me
    real_estate_categories= await load_real_estate_categories()
    if not(req.includedTypes!=[] and req.includedTypes!=[] and (set(req.includedTypes).intersection(set(real_estate_categories)))!=set()):
        # Create new dataset request
        req_dataset = ReqLocation(
            lat=city_data["lat"],
            lng=city_data["lng"],
            radius=30000,
            excludedTypes=req.excludedTypes,
            includedTypes=req.includedTypes,
            page_token=page_token,
            text_search=text_search,
        )

        # Fetch data from Google Maps API
        dataset, bknd_dataset_id, next_page_token, plan_name = await fetch_ggl_nearby(
            req_dataset, req_create_lyr=req
        )


        # Append new data to existing dataset
        existing_dataset.extend(dataset)

        # if request action was "full data" then store dataset id in the user profile
        # the name of the dataset will be the action + cct_layer name
        # make_ggl_layer_filename
        if req.action == "full data":
            user_data = load_user_profile(req.user_id)
            user_data["prdcer"]["prdcer_dataset"][
                plan_name.replace("plan_", "")
            ] = plan_name
            update_user_profile(req.user_id, user_data)

        trans_dataset = await MapBoxConnector.new_ggl_to_boxmap(dataset)
        trans_dataset["bknd_dataset_id"] = bknd_dataset_id
        trans_dataset["records_count"] = len(trans_dataset["features"])
        trans_dataset["prdcer_lyr_id"] = generate_layer_id()
        trans_dataset["next_page_token"] = next_page_token
        return trans_dataset
    else:
            existing_dataset={}
            req_dataset = ReqRealEstate(
                
                country_name=req.dataset_country,
                city_name=req.dataset_city,
                excludedTypes=req.excludedTypes,
                includedTypes=req.includedTypes,
                page_token=page_token,
                text_search=text_search,
            )

            # Fetch data from JSON files

            dataset, bknd_dataset_id, next_page_token, plan_name = await fetch_real_estate_nearby(
                req_dataset, req_create_lyr=req
            )
           
             # if request action was "full data" then store dataset id in the user profile
            # the name of the dataset will be the action + cct_layer name
            # make_ggl_layer_filename
            if req.action == "full data":
                user_data = load_user_profile(req.user_id)
                user_data["prdcer"]["prdcer_dataset"][
                    plan_name.replace("plan_", "")
                ] = plan_name
                update_user_profile(req.user_id, user_data)

            # Append new data to existing dataset
            existing_dataset.update(dataset)

            existing_dataset["bknd_dataset_id"] = bknd_dataset_id
            existing_dataset["records_count"] = len(existing_dataset["features"])
            existing_dataset["prdcer_lyr_id"] = generate_layer_id()
            existing_dataset["next_page_token"] = next_page_token
            return existing_dataset

async def save_lyr(req: ReqSavePrdcerLyer) -> str:
    try:
        user_data = load_user_profile(req.user_id)
    except FileNotFoundError as fnfe:
        logger.error(f"User profile not found for user_id: {req.user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found"
        ) from fnfe

    try:
        # Add the new layer to user profile
        user_data["prdcer"]["prdcer_lyrs"][req.prdcer_lyr_id] = req.dict(
            exclude={"user_id"}
        )

        # Save updated user data
        update_user_profile(req.user_id, user_data)
        update_dataset_layer_matching(req.prdcer_lyr_id, req.bknd_dataset_id)
        update_user_layer_matching(req.prdcer_lyr_id, req.user_id)
    except KeyError as ke:
        logger.error(f"Invalid user data structure for user_id: {req.user_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user data structure",
        ) from ke

    return "Producer layer created successfully"


@preserve_validate_decorator
@log_and_validate(logger, validate_output=True, output_model=List[LayerInfo])
async def fetch_user_lyrs(req: ReqUserId) -> List[LayerInfo]:
    """
    Retrieves all producer layers associated with a specific user. It reads the
    user's data file and the dataset-layer matching file to compile a list of
    all layers owned by the user, including metadata like layer name, color,
    and record count.
    """
    try:
        # Load dataset_layer_matching.json
        dataset_layer_matching = load_dataset_layer_matching()
    except FileNotFoundError as fnfe:
        logger.error("Dataset-layer matching file not found")
        raise HTTPException(
            status_code=500, detail="Dataset-layer matching data not available"
        ) from fnfe

    user_layers = fetch_user_layers(req.user_id)

    user_layers_metadata = []
    for lyr_id, lyr_data in user_layers.items():
        try:
            dataset_id, dataset_info = fetch_dataset_id(lyr_id, dataset_layer_matching)
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
        layer_owner_id = fetch_layer_owner(req.prdcer_lyr_id)
        layer_owner_data = load_user_profile(layer_owner_id)

        try:
            layer_metadata = layer_owner_data["prdcer"]["prdcer_lyrs"][
                req.prdcer_lyr_id
            ]
        except KeyError as ke:
            raise HTTPException(
                status_code=404, detail="Producer layer not found for this user"
            ) from ke

        dataset_id, dataset_info = fetch_dataset_id(req.prdcer_lyr_id)

        # if the dataset_id contains the word plan '21.57445341427591_39.1728_2000.0_mosque__plan_mosque_Saudi Arabia_Jeddah@#$9'
        # isolate the plan's name from the dataset_id = mosque__plan_mosque_Saudi Arabia_Jeddah
        # load the plan's json file
        # from the dataset_id isolate the page number which is after @#$ = 9
        # using the page number and the plan , load and concatenate all datasets from the plan that have page number equal to that number or less
        # each dataset is a list of dictionaries , so just extend the list  and save the big final list into dataset variable
        # else load dataset with dataset id
        if "plan" in dataset_id:
            # Extract plan name and page number
            plan_name, page_number = dataset_id.split("@#$")
            dataset, plan_name = plan_name.split("page_token=")
            page_number = int(page_number)
            # Load the plan
            plan = await get_plan(plan_name)
            if not plan:
                raise HTTPException(status_code=404, detail="Plan not found")
            # Initialize an empty list to store all datasets
            all_datasets = []
            # Load and concatenate all datasets up to the current page number
            for i in range(page_number):
                if i == 0:
                    continue
                dataset = await load_dataset(f"{plan[i]}_page_token={plan_name}@#${i}")
                all_datasets.extend(dataset)

        else:
            all_datasets = await load_dataset(dataset_id)
        trans_dataset = await MapBoxConnector.new_ggl_to_boxmap(all_datasets)

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
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An error occurred: {str(e)}"
        ) from e


async def create_save_prdcer_ctlg(req: ReqSavePrdcerCtlg) -> str:
    """
    Creates and saves a new producer catalog.
    """
    try:
        user_data = load_user_profile(req.user_id)

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
        update_user_profile(req.user_id, serializable_user_data)

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
        user_catalogs = fetch_user_catalogs(req.user_id)
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
        user_data = load_user_profile(req.user_id)
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

        dataset_layer_matching = load_dataset_layer_matching()
        ctlg_owner_data = load_user_profile(ctlg["ctlg_owner_user_id"])

        ctlg_lyrs_map_data = []
        for lyr_info in ctlg["lyrs"]:
            lyr_id = lyr_info["layer_id"]
            dataset_id, dataset_info = fetch_dataset_id(lyr_id, dataset_layer_matching)
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


async def apply_zone_layers(req: ReqApplyZoneLayers) -> List[PrdcerLyrMapData]:
    """
    Applies zone layer transformations to a set of layers.
    """
    try:
        non_zone_layers = req.lyrs.copy()
        zone_layers = []
        for layer in req.lyrs_as_zone:
            zone_lyr_id = list(layer.keys())[0]
            zone_layers.append(zone_lyr_id)
            non_zone_layers.remove(zone_lyr_id)

        dataset_layer_matching = load_dataset_layer_matching()

        non_zone_data = []
        for lyr_id in non_zone_layers:
            dataset_id, _ = fetch_dataset_id(lyr_id, dataset_layer_matching)
            if dataset_id:
                dataset = await load_dataset(dataset_id)
                lyr_data = await MapBoxConnector.new_ggl_to_boxmap(dataset)
                non_zone_data.extend(lyr_data["features"])

        zone_data = {}
        for lyr_id in zone_layers:
            dataset_id, _ = fetch_dataset_id(lyr_id, dataset_layer_matching)
            if dataset_id:
                dataset = await load_dataset(dataset_id)
                lyr_data = await MapBoxConnector.new_ggl_to_boxmap(dataset)
                zone_data[lyr_id] = lyr_data

        transformed_layers = []
        for layer in req.lyrs_as_zone:
            zone_lyr_id = list(layer.keys())[0]
            zone_property_key = list(layer.values())[0]
            zone_transformed = apply_zone_transformation(
                zone_data[zone_lyr_id], non_zone_data, zone_property_key, zone_lyr_id
            )
            transformed_layers.extend(zone_transformed)

        return transformed_layers
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An error occurred: {str(e)}"
        ) from e


def apply_zone_transformation(
    zone_layer_data: Dict[str, Any],
    non_zone_points: List[Dict[str, Any]],
    zone_property: str,
    zone_lyr_id: str,
) -> List[PrdcerLyrMapData]:
    """
    This function applies zone transformations to a set of points.
    """
    try:
        zone_property = zone_property.split("features.properties.")[-1]
        property_values = [
            feature["properties"].get(zone_property, 9191919191)
            for feature in zone_layer_data["features"]
        ]
        arr = np.array(property_values)
        avg = np.mean(arr[arr != 9191919191.0])
        new_arr = np.where(arr == 9191919191.0, avg, arr)
        property_values = new_arr.tolist()
        thresholds = calculate_thresholds(property_values)

        new_layers = [
            PrdcerLyrMapData(
                type="FeatureCollection",
                features=[],
                prdcer_layer_name=f"{zone_layer_data.get('prdcer_layer_name', 'Layer')} ({category})",
                prdcer_lyr_id=f"zy{zone_lyr_id}_applied_{i + 1}",
                points_color=color,
                layer_legend=f"{zone_layer_data.get('layer_legend', 'Layer')} {category} {zone_property}",
                records_count=0,
                is_zone_lyr="False",
                bknd_dataset_id=zone_layer_data.get("bknd_dataset_id", ""),
                layer_description=zone_layer_data.get("layer_description", ""),
            )
            for i, (category, color) in enumerate(
                [
                    ("low", "grey"),
                    ("medium", "cyan"),
                    ("high", "red"),
                    ("non-zone-overlap", "blue"),
                ]
            )
        ]

        for point in non_zone_points:
            point_coords = point["geometry"]["coordinates"]
            for zone_feature in zone_layer_data["features"]:
                zone_point = zone_feature["geometry"]["coordinates"]
                if calculate_distance_km(point_coords, zone_point) <= 2:
                    value = zone_feature["properties"].get(zone_property, 0)
                    if value <= thresholds[0]:
                        new_layers[0].features.append(create_feature(point))
                    elif value <= thresholds[1]:
                        new_layers[1].features.append(create_feature(point))
                    else:
                        new_layers[2].features.append(create_feature(point))
                    break
                else:
                    new_layers[3].features.append(create_feature(point))

        for layer in new_layers:
            layer.records_count = len(layer.features)

        return new_layers
    except Exception as e:
        raise ValueError(f"Error in apply_zone_transformation: {str(e)}")


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


def create_feature(point: Dict[str, Any]) -> Feature:
    """
    Converts a point dictionary into a Feature object. This function is used
    to ensure that all points are in the correct format for geospatial operations.
    """
    try:
        return Feature(
            type=point["type"],
            properties=point["properties"],
            geometry=Geometry(
                type="Point", coordinates=point["geometry"]["coordinates"]
            ),
        )
    except KeyError as e:
        raise ValueError(f"Invalid point data: missing key {str(e)}")
    except Exception as e:
        raise ValueError(f"Error creating feature: {str(e)}")


async def fetch_nearby_categories(req: None) -> Dict:
    """
    Provides a comprehensive list of nearby place categories, organized into
    broader categories. This function returns a large, predefined dictionary
    of categories and subcategories, covering various aspects of urban life
    such as automotive, culture, education, entertainment, and more.
    """
    google_categories = load_google_categories()
    real_estate_categories = await load_real_estate_categories()

    # combine google categories and real estate categories
    categories = {**google_categories, **real_estate_categories}

    return categories


# Apply the decorator to all functions in this module
apply_decorator_to_module(logger)(__name__)
