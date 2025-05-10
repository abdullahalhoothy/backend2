import aiohttp
import logging
from typing import List, Dict, Any, Tuple, Optional
import json
import asyncio
from fastapi import HTTPException
import requests
from all_types.myapi_dtypes import ReqStreeViewCheck, ReqFetchDataset
from backend_common.utils.utils import convert_strings_to_ints
from config_factory import CONF
from backend_common.logging_wrapper import apply_decorator_to_module
from all_types.response_dtypes import (
    LegInfo,
    TrafficCondition,
    RouteInfo,
)
from boolean_query_processor import optimize_query_sequence, separate_boolean_queries,text_search_query_sequence
from geo_std_utils import fetch_lat_lng_bounding_box
from mapbox_connector import MapBoxConnector
from popularity_algo import process_req_plan, rectify_plan
from storage import load_dataset, make_dataset_filename, make_dataset_filename_part, store_data_resp
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)



# Load and flatten the popularity data
with open("Backend/ggl_categories_poi_estimate.json", "r") as f:
    raw_popularity_data = json.load(f)

# Flatten the nested dictionary - we only care about subkeys
POPULARITY_DATA = {}
for category in raw_popularity_data.values():
    POPULARITY_DATA.update(category)


async def fetch_text_search_ggl_maps_api(req: ReqFetchDataset, 
                                     optimized_queries:List[Tuple[List[str], List[str]]]
                                     ) -> Tuple[List[Dict[str, Any]], str]:
    # check if the entire dataset with all include exclude is available in db
    # if not check if partial with both include and exclude is available in db
    # if not check if seperate include & exclude is available in db

    # if retriving seperate include & exclude, if not empty then combine them into partial dataset and save it in db
    # if retriving partial dataset or built partial dataset,and if not empty then combine them into full dataset and save it in db
    combined_dataset_id = make_dataset_filename(req, text_search=True)
    existing_combined_data = await load_dataset(combined_dataset_id)
    
    if existing_combined_data:
        logger.info(f"Returning existing combined dataset: {combined_dataset_id}")
        return existing_combined_data

    separte_parts_datasets = {}
    missing_queries = {}
    all_missing_query_results = {}

    for included_terms, excluded_terms in optimized_queries:
        partial_dataset_id = make_dataset_filename_part(req, included_terms, excluded_terms)
        stored_data = await load_dataset(partial_dataset_id)

        if stored_data:
            separte_parts_datasets[partial_dataset_id] = stored_data
        else:
            if included_terms:
                include_dataset_id = make_dataset_filename_part(req, included_terms, [])
                if include_dataset_id not in missing_queries and include_dataset_id not in separte_parts_datasets:
                    include_stored_data = await load_dataset(include_dataset_id)
                    if include_stored_data:
                        separte_parts_datasets[include_dataset_id] = include_stored_data
                    else:
                        missing_queries[include_dataset_id] = (included_terms, [])
                
            if excluded_terms:
                exclude_dataset_id = make_dataset_filename_part(req, [], excluded_terms)
                # not already added to missing_queries or datasets
                if exclude_dataset_id not in missing_queries and exclude_dataset_id not in separte_parts_datasets:
                    exclude_stored_data = await load_dataset(exclude_dataset_id)
                    if exclude_stored_data:
                        separte_parts_datasets[exclude_dataset_id] = exclude_stored_data
                    else:
                        missing_queries[exclude_dataset_id] = ([], excluded_terms)


    if missing_queries:
        logger.info(f"Fetching {len(missing_queries)} queries from Google Maps API.")
        query_tasks = []
        for dataset_id, inc_exc in missing_queries.items():
            included_terms, excluded_terms = inc_exc
            if included_terms:
                text_query = included_terms[0] 
            else:
                text_query = excluded_terms[0]
            response_dict = single_ggl_text_call(req, text_query, dataset_id)
            query_tasks.append(response_dict)          


        all_missing_responses = await asyncio.gather(*query_tasks)

        # combine list of dicts into a single dict
        all_missing_query_results = {k: v for d in all_missing_responses for k, v in d.items()}

        for dataset_id, query_results in all_missing_query_results.items():
            # convert the results into the format required by MapBoxConnector
            # for each result, save the part seperately in db
            if query_results:  
                format_response = await MapBoxConnector.new_ggl_to_boxmap(query_results,req.radius)
                format_response = convert_strings_to_ints(format_response)
                await store_data_resp(req, format_response, dataset_id)
                separte_parts_datasets[dataset_id] = format_response
        

    # recreate the partial dataset from the include and exclude datasets and save into db
    datasets = {}
    for included_terms, excluded_terms in optimized_queries:
        include_dataset_id = make_dataset_filename_part(req, included_terms, [])
        exclude_dataset_id = make_dataset_filename_part(req, [], excluded_terms)
        # ensure dataset is available either from separte_parts_datasets or if not from db
        if separte_parts_datasets.get(include_dataset_id):
            include_dataset = separte_parts_datasets.get(include_dataset_id)
        else:
            include_dataset = await load_dataset(include_dataset_id)
        
        if separte_parts_datasets.get(exclude_dataset_id):
            exclude_dataset = separte_parts_datasets.get(exclude_dataset_id)
        else:
            exclude_dataset = await load_dataset(exclude_dataset_id)
        

        partial_dataset_id = make_dataset_filename_part(req, included_terms, excluded_terms)
        # datasets[partial_dataset_id] is all of include dataset after removing the exclude dataset
        # if there is data in include dataset, else datasets[partial_dataset_id] = {}
        if include_dataset:
            if exclude_dataset:
                ids_to_exclude = set()
                for place in exclude_dataset.get("features"):
                    ids_to_exclude.add(place.get('properties', {}).get('id'))

                # filter the include dataset to remove the exclude dataset
                filtered_places = []
                for place in include_dataset.get("features"):
                    place_id = place.get('properties', {}).get('id') 
                    if place_id not in ids_to_exclude:
                        filtered_places.append(place)
            
                if filtered_places:
                    filtered_include_dataset = {
                        'type': 'FeatureCollection',
                        'features': filtered_places,
                        'properties': include_dataset.get('properties', [])
                    }
                    await store_data_resp(req, filtered_include_dataset, partial_dataset_id)
                    datasets[partial_dataset_id] = filtered_include_dataset
            else:
                datasets[partial_dataset_id] = include_dataset
        else:
            datasets[partial_dataset_id] = {}


    # Initialize the combined dictionary
    combined = {
        'type': 'FeatureCollection',
        'features': [],
        'properties': set()
    }

    # Initialize a set to keep track of unique IDs
    seen_ids = set()

    # Iterate through each dataset
    for data in datasets.values():
        # Add properties to the combined set
        combined['properties'].update(data.get('properties', []))
        features = data.get('features', [])
        
        # Iterate through each feature in the dataset
        for feature in features:
            feature_id = feature.get('properties', {}).get('id')
            if feature_id is not None and feature_id not in seen_ids:
                combined['features'].append(feature)
                seen_ids.add(feature_id)

    # Convert the properties set back to a list (if needed)
    combined['properties'] = list(combined['properties'])

    if combined:
        await store_data_resp(req, combined, combined_dataset_id)
        for feature in combined['features']:
            if 'properties' in feature and 'id' in feature['properties']:
                del feature['properties']['id']
        logger.info(f"Stored combined dataset: {combined_dataset_id}")
        return combined
    else:
        logger.warning("No valid results returned from Google Maps API or DB.")
        return combined



async def fetch_from_google_maps_api(req: ReqFetchDataset, 
                                     optimized_queries:List[Tuple[List[str], List[str]]]
                                     ) -> Tuple[List[Dict[str, Any]], str]:
    try:

        combined_dataset_id = make_dataset_filename(req)
        existing_combined_data = await load_dataset(combined_dataset_id)
        
        if existing_combined_data:
            logger.info(f"Returning existing combined dataset: {combined_dataset_id}")
            return existing_combined_data

        datasets = {}
        missing_queries = []
        

        for included_types, excluded_types in optimized_queries:
            full_dataset_id = make_dataset_filename_part(req, included_types, excluded_types)
            stored_data = await load_dataset(full_dataset_id)

            if stored_data:
                datasets[full_dataset_id] = stored_data
            else:
                missing_queries.append((full_dataset_id, included_types, excluded_types))

        if missing_queries:
            logger.info(f"Fetching {len(missing_queries)} queries from Google Maps API.")
            query_tasks = [
                    single_ggl_cat_call(req, included_types, excluded_types)
                    for _, included_types, excluded_types in missing_queries
                ]

            all_query_results = await asyncio.gather(*query_tasks)

            for (dataset_id, included, excluded), query_results in zip(missing_queries, all_query_results):
                    
                if query_results:  
                    dataset = await MapBoxConnector.new_ggl_to_boxmap(query_results,req.radius)
                    dataset = convert_strings_to_ints(dataset)
                    await store_data_resp(req, dataset, dataset_id)
                    datasets[dataset_id] = dataset

        # Initialize the combined dictionary
        combined = {
            'type': 'FeatureCollection',
            'features': [],
            'properties': set()
        }

        # Initialize a set to keep track of unique IDs
        seen_ids = set()

        # Iterate through each dataset
        for dataset in datasets.values():
            # Add properties to the combined set
            combined['properties'].update(dataset.get('properties', []))
            features = dataset.get('features', [])
            
            # Iterate through each feature in the dataset
            for feature in features:
                feature_id = feature.get('properties', {}).get('id')
                if feature_id is not None and feature_id not in seen_ids:
                    combined['features'].append(feature)
                    seen_ids.add(feature_id)

        # Convert the properties set back to a list (if needed)
        combined['properties'] = list(combined['properties'])

        if combined:
            await store_data_resp(req, combined, combined_dataset_id)
            for feature in combined['features']:
                if 'properties' in feature and 'id' in feature['properties']:
                    del feature['properties']['id']
            logger.info(f"Stored combined dataset: {combined_dataset_id}")
            return combined
        else:
            logger.warning("No valid results returned from Google Maps API or DB.")
            return combined

    except Exception as e:
        logger.error(f"Error in fetch_from_google_maps_api: {str(e)}")
        return str(e)

async def build_text_search_payload(req: ReqFetchDataset, textQuery) -> Dict[str, Any]:
    ggl_api_url = CONF.search_text
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": CONF.api_key,
        "X-Goog-FieldMask": CONF.google_fields+",nextPageToken",
    }
    data = {
        "textQuery": textQuery,
        "locationBias": {
            "circle": {
                    "center": {
                        "latitude": req.lat,
                        "longitude": req.lng,
                    },
                    "radius": req.radius,
                }
        },
    }
    return ggl_api_url, headers, data


async def build_category_search_payload(req: ReqFetchDataset, include: List[str], exclude: List[str]) -> Dict[str, Any]:
    ggl_api_url = CONF.nearby_search
    data = {
        "includedTypes": include,
        "excludedTypes": exclude,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": req.lat,
                    "longitude": req.lng,
                },
                "radius": req.radius,
            }
        },
    }

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": CONF.api_key,
        "X-Goog-FieldMask": CONF.google_fields,
    }

    return ggl_api_url, headers, data

async def make_api_call(ggl_api_url, headers, data):
    try:
        async with aiohttp.ClientSession() as session:
            logger.info(f"Request URL: {ggl_api_url}")
            logger.info(f"Request Data: {data}")
            async with session.post(
                ggl_api_url, headers=headers, json=data) as response:
                if response.status == 200:
                    response_data = await response.json()
                    results = response_data.get("places", [])
                    logger.info(f"Query returned {len(results)} results")
                    return results
                else:
                    error_msg = await response.text()
                    logger.error(f"API request failed: {error_msg}")
                    return []

    except aiohttp.ClientError as e:
        # TODO this doesn't reraise the error, not sure what to do about it
        logger.error(f"Network error during API request: {str(e)}")
        return []

async def single_ggl_text_call(req: ReqFetchDataset, text_query:str, id:str) -> List[dict]:
    ggl_api_url, headers, include_body = await build_text_search_payload(req, text_query)
    logger.info(f"text search for include term: {text_query}")
    results = await make_api_call(ggl_api_url, headers, include_body)
    return {id:results}


async def single_ggl_cat_call(
    req: ReqFetchDataset, include: List[str], exclude: List[str], text_search=False
) -> List[dict]:
    ggl_api_url, headers, data = await build_category_search_payload(req, include, exclude)
    logger.info(f"Executing query - Include: {include}, Exclude: {exclude}")

    results = await make_api_call(ggl_api_url, headers, data)

    return results






async def text_fetch_from_google_maps_api(req: ReqFetchDataset,) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": CONF.api_key,
        "X-Goog-FieldMask": CONF.google_fields+",nextPageToken",
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


async def query_ggl(req:ReqFetchDataset, search_type: str) -> Tuple[List[Dict[str, Any]], str]:
    # seperate category boolean query from keyword boolean query, keyword are wraped in @, and category are not. another clue is space category keywords don't have space
    # for example      boolean ="""(auto_parts_store OR @auto parts@ OR @car repair@ OR @car parts@ OR @car repair parts@ OR @قطع غيار السيارات@) AND NOT @بنشر@"""
    # category boolean should be  = """(auto_parts_store)"""
    # keyword boolean should be  = """(@auto parts@ OR @car repair@ OR @car parts@ OR @car repair parts@ OR @قطع غيار السيارات@) AND NOT @بنشر@"""
    cat_boolean, kw_boolean = separate_boolean_queries(req.boolean_query)

    if "default" in search_type or "category_search" in search_type:
        cat_optimized_queries = optimize_query_sequence(cat_boolean, POPULARITY_DATA)
        dataset = await fetch_from_google_maps_api(req, cat_optimized_queries)
    if "keyword_search" in search_type:
        kw_optimized_queries = text_search_query_sequence(kw_boolean)
        dataset = await fetch_text_search_ggl_maps_api(req, kw_optimized_queries)
        # ggl_api_resp, _ = await text_fetch_from_google_maps_api(req, kw_optimized_queries)
        # dataset = await MapBoxConnector.new_ggl_to_boxmap(ggl_api_resp, req.radius)
        # if ggl_api_resp:
        #     dataset = convert_strings_to_ints(dataset)
    return dataset





async def fetch_ggl_nearby(req: ReqFetchDataset):
    search_type = req.search_type
    action = req.action
    plan_name = ""
    next_plan_index = 0

    # try 30 times to get non empty dataset
    for _ in range(30):
        next_page_token = req.page_token

        if req.action == "full data":
            req, plan_name, next_page_token, current_plan_index, bknd_dataset_id = (
                await process_req_plan(req)
            )
        else:
            req = fetch_lat_lng_bounding_box(req)

        bknd_dataset_id = make_dataset_filename(req)

        dataset = await query_ggl(req, search_type)

        if req.action == "full data" and dataset:
            if len(dataset.get("features", "")) == 0:
                next_plan_index = await rectify_plan(plan_name, current_plan_index)
                if next_plan_index == "":
                    break
                else:
                    req.page_token = (
                        req.page_token.split("@#$")[0] + "@#$" + str(next_plan_index)
                    )
            else:
                # continue as usual
                break

    # if dataset is less than 20 or none and action is full data
    if len(dataset.get("features", "")) < 20 and action == "full data":
        next_plan_index = await rectify_plan(plan_name, current_plan_index)
        if next_plan_index == "":
            next_page_token = ""
        else:
            next_page_token = (
                next_page_token.split("@#$")[0] + "@#$" + str(next_plan_index)
            )

    # next_plan_index = whichever greater between next_plan_index and current_plan_index+1
    if current_plan_index + 1 > next_plan_index:
        next_plan_index = current_plan_index + 1

    return dataset, bknd_dataset_id, next_page_token, plan_name, next_plan_index


# Apply the decorator to all functions in this module
apply_decorator_to_module(logger)(__name__)