import logging
import uuid
from datetime import datetime, date, timedelta, timezone
from typing import Any, Dict, Tuple, Optional, List
import json
import os

from fastapi import HTTPException, status
from pydantic import BaseModel
from backend_common.auth import load_user_profile
from backend_common.database import Database
import pandas as pd
from sql_object import SqlObject
from all_types.myapi_dtypes import ReqFetchDataset
from backend_common.logging_wrapper import apply_decorator_to_module
from backend_common.auth import db
import asyncpg
from backend_common.background import get_background_tasks
import orjson
from popularity_algo import create_plan, get_plan

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

BACKEND_DIR = "Backend/real_estate_storage"
USERS_PATH = "Backend/users"
STORE_CATALOGS_PATH = "Backend/store_catalogs.json"
DATASET_LAYER_MATCHING_PATH = "Backend/dataset_layer_matching.json"
DATASETS_PATH = "Backend/datasets"
USER_LAYER_MATCHING_PATH = "Backend/user_layer_matching.json"
METASTORE_PATH = "Backend/layer_category_country_city_matching"
STORAGE_DIR = "Backend/storage"
COLOR_PATH = "Backend/gradient_colors.json"
USERS_INFO_PATH = "Backend/users_info.json"
RIYADH_VILLA_ALLROOMS = "Backend/riyadh_villa_allrooms.json"  # to be change to real estate id needed
GOOGLE_CATEGORIES_PATH = "Backend/google_categories.json"
REAL_ESTATE_CATEGORIES_PATH = "Backend/real_estate_categories.json"
# Add a new constant for census categories path
area_intelligence_categories_PATH = "Backend/area_intelligence_categories.json"
# Map census types to their respective CSV files
CENSUS_FILE_MAPPING = {
    "household": "Backend/census_data/Final_household_all.csv",
    "population": "Backend/census_data/Final_population_all.csv",
    "housing": "Backend/census_data/Final_housing_all.csv",
    "economic": "Backend/census_data/Final_economic_all.csv",
}

DEFAULT_LIMIT = 20

os.makedirs(STORAGE_DIR, exist_ok=True)


with open(GOOGLE_CATEGORIES_PATH, "r") as f:
    GOOGLE_CATEGORIES = json.load(f)
with open(REAL_ESTATE_CATEGORIES_PATH, "r") as f:
    REAL_ESTATE_CATEGORIES = json.load(f)
with open(area_intelligence_categories_PATH, "r") as f:
    AREA_INTELLIGENCE_CATEGORIES = json.load(f)
with open(COLOR_PATH, "r") as f:
    GRADIENT_COLORS = json.load(f)


def to_serializable(obj: Any) -> Any:
    """
    Convert a Pydantic model or any other object to a JSON-serializable format.

    Args:
    obj (Any): The object to convert.

    Returns:
    Any: A JSON-serializable representation of the object.
    """
    if isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(to_serializable(item) for item in obj)
    elif isinstance(obj, BaseModel):
        return to_serializable(obj.dict(by_alias=True))
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif hasattr(obj, "__dict__"):
        return to_serializable(obj.__dict__)
    else:
        return obj


def convert_to_serializable(obj: Any) -> Any:
    """
    Convert an object to a JSON-serializable format and verify serializability.

    Args:
    obj (Any): The object to convert.

    Returns:
    Any: A JSON-serializable representation of the object.

    Raises:
    ValueError: If the object cannot be serialized to JSON.
    """
    try:
        serializable_obj = to_serializable(obj)
        json.dumps(serializable_obj)
        return serializable_obj
    except (TypeError, OverflowError, ValueError) as e:
        raise ValueError(f"Object is not JSON serializable: {str(e)}")


def make_include_exclude_name(include_list, exclude_list):
    excluded_str = ",".join(exclude_list)
    included_str = ",".join(include_list)

    type_string = f"include={included_str}_exclude={excluded_str}"
    return type_string


def make_ggl_dataset_cord_string(lng: str, lat: str, radius: str):
    return f"{lng}_{lat}_{radius}"


def make_dataset_filename(req: ReqFetchDataset, text_search=False) -> str:
    if req:
        cord_string = make_ggl_dataset_cord_string(req.lng, req.lat, req.radius)
        # type_string = make_include_exclude_name(req.includedTypes, req.excludedTypes)
        type_string = req.boolean_query.replace(" ", "_")
        try:
            name = f"{cord_string}_{type_string}_token={req.page_token}"
            if text_search:
                name = name + f"_text_search=true_"

        except AttributeError as e:
            raise ValueError(f"Invalid location request object: {str(e)}")

    return name


def make_dataset_filename_part(
    req: ReqFetchDataset, included_types: List[str], excluded_types: List[str]
) -> str:
    """Generate unique dataset ID based on query terms."""
    cord_string = make_ggl_dataset_cord_string(req.lng, req.lat, req.radius)
    type_string = ""
    if included_types:
        include_str = "_".join(sorted(included_types))
        type_string = type_string + f"including_{include_str}"
    if excluded_types:
        exclude_str = "_".join(sorted(excluded_types))
        type_string = type_string + f"excluding_{exclude_str}"
    return f"{cord_string}_{type_string}"


async def fetch_dataset_id(lyr_id: str) -> Tuple[str, Dict]:
    """
    Searches for the dataset ID associated with a given layer ID.
    """
    dataset_layer_matching = await load_dataset_layer_matching()

    for d_id, dataset_info in dataset_layer_matching.items():
        if lyr_id in dataset_info["prdcer_lyrs"]:
            return d_id, dataset_info
    # raise HTTPException(
    #     status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found for this layer"
    # )


def fetch_layer_owner(prdcer_lyr_id: str) -> str:
    """
    Fetches the owner of a layer based on the producer layer ID.
    """
    with open(USER_LAYER_MATCHING_PATH, "r") as f:
        user_layer_matching = json.load(f)
    layer_owner_id = user_layer_matching.get(prdcer_lyr_id)
    if not layer_owner_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Layer owner not found",
        )
    return layer_owner_id


# def load_dataset_layer_matching() -> Dict:
#     """ """
#     try:
#         with open(DATASET_LAYER_MATCHING_PATH, "r") as f:
#             dataset_layer_matching = json.load(f)
#         return dataset_layer_matching
#     except FileNotFoundError:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Dataset layer matching file not found",
#         )
#     except json.JSONDecodeError:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Error parsing dataset layer matching file",
#         )


# def update_dataset_layer_matching(
#     prdcer_lyr_id: str, bknd_dataset_id: str, records_count: int = 9191919
# ):
#     try:
#         if os.path.exists(DATASET_LAYER_MATCHING_PATH):
#             with open(DATASET_LAYER_MATCHING_PATH, "r") as f:
#                 dataset_layer_matching = json.load(f)
#         else:
#             dataset_layer_matching = {}

#         if bknd_dataset_id not in dataset_layer_matching:
#             dataset_layer_matching[bknd_dataset_id] = {
#                 "records_count": records_count,
#                 "prdcer_lyrs": [],
#             }

#         if prdcer_lyr_id not in dataset_layer_matching[bknd_dataset_id]["prdcer_lyrs"]:
#             dataset_layer_matching[bknd_dataset_id]["prdcer_lyrs"].append(prdcer_lyr_id)

#         dataset_layer_matching[bknd_dataset_id]["records_count"] = records_count

#         with open(DATASET_LAYER_MATCHING_PATH, "w") as f:
#             json.dump(dataset_layer_matching, f, indent=2)
#     except IOError:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Error updating dataset layer matching",
#         )


# def update_user_layer_matching(layer_id: str, layer_owner_id: str):
#     try:
#         with open(USER_LAYER_MATCHING_PATH, "r+") as f:
#             user_layer_matching = json.load(f)
#             user_layer_matching[layer_id] = layer_owner_id
#             f.seek(0)
#             json.dump(user_layer_matching, f, indent=2)
#             f.truncate()
#     except IOError:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Error updating user layer matching",
#         )


async def load_dataset_layer_matching() -> Dict:
    """Load dataset layer matching from Firestore"""
    try:
        return await db.get_document("layer_matchings", "dataset_matching")
    except HTTPException as e:
        if e.status_code == status.HTTP_404_NOT_FOUND:
            return {}
        raise e


async def update_dataset_layer_matching(
    prdcer_lyr_id: str, bknd_dataset_id: str, records_count: int = 9191919
):
    collection_name = "layer_matchings"
    document_id = "dataset_matching"

    try:
        dataset_layer_matching = await db.get_document(
            collection_name, document_id
        )
    except HTTPException as e:
        if e.status_code == status.HTTP_404_NOT_FOUND:
            dataset_layer_matching = {}
        else:
            raise e

    if bknd_dataset_id not in dataset_layer_matching:
        dataset_layer_matching[bknd_dataset_id] = {
            "records_count": records_count,
            "prdcer_lyrs": [],
        }

    if (
        prdcer_lyr_id
        not in dataset_layer_matching[bknd_dataset_id]["prdcer_lyrs"]
    ):
        dataset_layer_matching[bknd_dataset_id]["prdcer_lyrs"].append(
            prdcer_lyr_id
        )

    dataset_layer_matching[bknd_dataset_id]["records_count"] = records_count

    # Update cache immediately
    db._cache[collection_name][document_id] = dataset_layer_matching

    async def _background_update():
        doc_ref = (
            db.get_async_client()
            .collection(collection_name)
            .document(document_id)
        )
        await doc_ref.set(dataset_layer_matching)

    get_background_tasks().add_task(_background_update)
    return dataset_layer_matching


async def delete_dataset_layer_matching(
    prdcer_lyr_id: str, bknd_dataset_id: str, records_count: int = 9191919
):
    collection_name = "layer_matchings"
    document_id = "dataset_matching"

    try:
        dataset_layer_matching = await db.get_document(
            collection_name, document_id
        )
    except HTTPException as e:
        if e.status_code == status.HTTP_404_NOT_FOUND:
            dataset_layer_matching = {}
        else:
            raise e

    if bknd_dataset_id not in dataset_layer_matching:
        dataset_layer_matching[bknd_dataset_id] = {
            "records_count": records_count,
            "prdcer_lyrs": [],
        }

    # Check if the producer layer exists in the dataset
    if (
        prdcer_lyr_id
        not in dataset_layer_matching[bknd_dataset_id]["prdcer_lyrs"]
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Layer {prdcer_lyr_id} not found in dataset {bknd_dataset_id}",
        )

    # Remove the layer ID from the dataset's 'prdcer_lyrs' list
    dataset_layer_matching[bknd_dataset_id]["prdcer_lyrs"].remove(prdcer_lyr_id)

    # Update cache immediately
    db._cache[collection_name][document_id] = dataset_layer_matching

    async def _background_update():
        # Update the dataset layer matching document in the database
        doc_ref = (
            db.get_async_client()
            .collection(collection_name)
            .document(document_id)
        )
        await doc_ref.set(dataset_layer_matching)

    # Run background task to persist the changes in the database
    get_background_tasks().add_task(_background_update)

    return {
        "message": f"Layer {prdcer_lyr_id} removed from dataset {bknd_dataset_id} successfully"
    }


async def load_user_layer_matching() -> Dict:
    """Load user layer matching from Firestore"""
    try:
        return await db.get_document("layer_matchings", "user_matching")
    except HTTPException as e:
        if e.status_code == status.HTTP_404_NOT_FOUND:
            return {}
        raise e


async def update_user_layer_matching(layer_id: str, layer_owner_id: str):
    collection_name = "layer_matchings"
    document_id = "user_matching"

    try:
        user_layer_matching = await db.get_document(
            collection_name, document_id
        )
    except HTTPException as e:
        if e.status_code == status.HTTP_404_NOT_FOUND:
            user_layer_matching = {}
        else:
            raise e

    user_layer_matching[layer_id] = layer_owner_id

    # Update cache immediately
    db._cache[collection_name][document_id] = user_layer_matching

    async def _background_update():
        doc_ref = (
            db.get_async_client()
            .collection(collection_name)
            .document(document_id)
        )
        await doc_ref.set(user_layer_matching)

    get_background_tasks().add_task(_background_update)
    return user_layer_matching


async def delete_user_layer_matching(layer_id: str):
    collection_name = "layer_matchings"
    document_id = "user_matching"

    try:
        # Fetch the current layer matching data
        user_layer_matching = await db.get_document(
            collection_name, document_id
        )
    except HTTPException as e:
        # Handle cases where the document is not found
        if e.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User layer matching document not found",
            )
        else:
            raise e

    # Check if the layer_id exists in the mapping
    if layer_id not in user_layer_matching:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Layer {layer_id} not found in the user layer matching.",
        )

    # Remove the layer from the user_layer_matching
    del user_layer_matching[layer_id]

    # Update cache immediately
    db._cache[collection_name][document_id] = user_layer_matching

    # Background update to persist the change in the database
    async def _background_update():
        doc_ref = (
            db.get_async_client()
            .collection(collection_name)
            .document(document_id)
        )
        await doc_ref.set(user_layer_matching)

    get_background_tasks().add_task(_background_update)
    return {"message": f"Layer {layer_id} removed successfully."}


async def fetch_user_layers(user_id: str) -> Dict[str, Any]:
    try:
        user_data = await load_user_profile(user_id)
        user_layers = user_data.get("prdcer", {}).get("prdcer_lyrs", {})
        return user_layers
    except FileNotFoundError as fnfe:
        logger.error(f"User layers not found for user_id: {user_id}")
        raise HTTPException(
            status_code=404, detail="User layers not found"
        ) from fnfe


async def fetch_user_catalogs(user_id: str) -> Dict[str, Any]:

    user_data = await load_user_profile(user_id)
    user_catalogs = user_data.get("prdcer", {}).get("prdcer_ctlgs", {})
    return user_catalogs


# def create_new_user(user_id: str, username: str, email: str) -> None:
#     user_file_path = os.path.join(USERS_PATH, f"user_{user_id}.json")

#     if os.path.exists(user_file_path):
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="User profile already exists",
#         )

#     user_data = {
#         "user_id": user_id,
#         "username": username,
#         "email": email,
#         "prdcer": {"prdcer_lyrs": {}, "prdcer_ctlgs": {}},
#     }

#     try:
#         with open(user_file_path, "w") as f:
#             json.dump(user_data, f, indent=2)
#     except IOError:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Error creating new user profile",
#         )


def load_store_catalogs() -> Dict[str, Any]:
    try:
        with open(STORE_CATALOGS_PATH, "r") as f:
            store_ctlgs = json.load(f)
        return store_ctlgs
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store catalogs file not found",
        )


def update_metastore(ccc_filename: str, bknd_dataset_id: str):
    """Update the metastore with the new layer information"""
    if bknd_dataset_id is not None:
        metastore_data = {
            "bknd_dataset_id": bknd_dataset_id,
            "created_at": datetime.now().isoformat(),
        }
        with open(f"{METASTORE_PATH}/{ccc_filename}", "w") as f:
            json.dump(metastore_data, f)


def get_country_code(country_name: str) -> str:
    country_codes = {
        "United Arab Emirates": "AE",
        "Saudi Arabia": "SA",
        "Canada": "CA",
    }
    return country_codes.get(country_name, "")


def generate_layer_id() -> str:
    return "l" + str(uuid.uuid4())


# async def create_real_estate_plan(req: ReqRealEstate) -> list[str]:
#     country = req.country_name.lower().replace(" ", "_")
#     folder_path = (
#         f"{BACKEND_DIR}/{country}/{req.city_name.lower()}/{req.includedTypes[0]}"
#     )
#     files = os.listdir(folder_path)
#     files = [file.split(".json")[0] for file in files]
#     return files


def remove_exclusions_from_id(dataset_id: str) -> str:
    """Removes 'excluding_*' from the dataset ID to find a broader match."""
    parts = dataset_id.split("_")
    filtered_parts = [p for p in parts if not p.startswith("excluding")]
    return "_".join(filtered_parts)


async def store_data_resp(
    req: ReqFetchDataset, dataset: Dict, file_name: str
) -> str:
    """
    Stores Google Maps data in the database, creating the table if needed.

    Args:
        req: Location request object
        dataset: Response data from Google Maps

    Returns:
        str: Filename/ID used as the primary key
    """
    try:
        # Convert request object to dictionary using Pydantic's model_dump
        req_dict = req.model_dump()

        await Database.execute(
            SqlObject.store_dataset,
            file_name,
            json.dumps(req_dict),
            json.dumps(dataset),
            datetime.utcnow(),
        )

        return file_name

    except asyncpg.exceptions.UndefinedTableError:
        # If table doesn't exist, create it and retry
        await Database.execute(SqlObject.create_datasets_table)
        return await store_data_resp(req, dataset, file_name)


async def load_dataset(dataset_id: str, fetch_full_plan_datasets=False) -> Dict:
    """
    Loads a dataset from file based on its ID.
    """
    # if the dataset_id contains the word plan '21.57445341427591_39.1728_2000.0_mosque__plan_mosque_Saudi Arabia_Jeddah@#$9'
    # isolate the plan's name from the dataset_id = mosque__plan_mosque_Saudi Arabia_Jeddah
    # load the plan's json file
    # from the dataset_id isolate the page number which is after @#$ = 9
    # using the page number and the plan , load and concatenate all datasets from the plan that have page number equal to that number or less
    # each dataset is a list of dictionaries , so just extend the list  and save the big final list into dataset variable
    # else load dataset with dataset id
    three_months_ago = datetime.now(timezone.utc) - timedelta(days=90)

    if "plan" in dataset_id and fetch_full_plan_datasets:
        # Extract plan name and page number
        if "@#$" in dataset_id:
            plan_name, page_number = dataset_id.split("@#$")
            dataset_prefix, plan_name = plan_name.split("page_token=")
            page_number = int(page_number)
        else:
            plan_name = dataset_id
            # TODO bad assumption below to say it's at max 100 different paginations but this is for perrformance now
            page_number = 100
        # Load the plan
        plan = await get_plan(plan_name)
        if not plan:
            return {}
        # if not plan:
        #     city_info=load_country_city()
        #     category = plan_name.split("_")[1]
        #     country_name = plan_name.split("_")[2]
        #     city_name = plan_name.split("_")[3]

        #     lng=city_info[f"{country_name}"][f"{city_name}"]["lat"]
        #     lat=city_info[f"{country_name}"][f"{city_name}"]["lat"]
        #     radius=ReqFetchDataset.model_fields["radius"].default
        #     boolean_query=category
        #     text_search=""
        #     plan = await create_plan(
        #         lng, lat, radius, boolean_query, text_search
        #     )

        # TODO this is a temp fix because this whole thing needs to be redone
        new_plan = []
        for i, item in enumerate(plan):
            if item == "end of search plan":
                continue

            first_parts = item.split("_", 3)
            lat, lon, value, rest = first_parts
            category = rest.split("_circle=")[0].replace(" ", "_")

            if i == 0:
                new_item = f"{lat}_{lon}_{value}_{category}_token="
            else:
                new_item = f"{lat}_{lon}_{value}_{category}_token=page_token={plan_name}@#${i}"

            new_plan.append(new_item)

        # Initialize an empty list to store all datasets
        all_features = []
        feat_collec = {"type": "FeatureCollection", "features": []}
        properties_set = set()  # Initialize a set to store unique properties
        for i in range(page_number):
            dataset_id = new_plan[i]  # Get the formatted item for this page
            json_content = await Database.fetchrow(
                SqlObject.load_dataset_with_timestamp, dataset_id
            )
            if json_content:
                created_at = json_content.get("created_at")
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                if created_at and created_at < three_months_ago:
                    await Database.execute(SqlObject.delete_dataset, dataset_id)
                    json_content = None
            if json_content:
                dataset = orjson.loads(json_content.get("response_data", "{}"))
                all_features.extend(dataset.get("features", []))
                properties_set.update(dataset.get("properties", []))
        if all_features:
            # Create the final combined GeoJSON
            feat_collec["features"] = all_features
            feat_collec["properties"] = list(properties_set)
    else:
        feat_collec = None
        json_content = await Database.fetchrow(
            SqlObject.load_dataset_with_timestamp, dataset_id
        )
        if json_content:
            created_at = json_content.get("created_at")
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            if created_at and created_at < three_months_ago:
                await Database.execute(SqlObject.delete_dataset, dataset_id)
                json_content = None

        if json_content:
            feat_collec = orjson.loads(json_content.get("response_data", "{}"))

    return feat_collec


async def get_census_dataset_from_storage(
    filename: str,
    action: str,
    request_location: ReqFetchDataset,
    next_page_token: str,
    data_type: str,
) -> tuple[dict, str, str]:
    """
    Retrieves census data from CSV files based on the data type requested.
    Returns data in GeoJSON format for consistency with other dataset types.
    """

    # Determine which CSV file to use based on included types
    # data_type = req.included_types[0]  # Using first type for now

    if data_type in ["Population Area Intelligence"]:
        query = SqlObject.census_w_bounding_box
    # elif data_type in ["Housing Area Intelligence"]:
    #     query = SqlObject.census_w_bounding_box
    # elif data_type in ["Income Area Intelligence"]:
    #     query = SqlObject.economic_w_bounding_box

    city_data = await Database.fetch(
        query, *request_location._bounding_box, request_location.zoom_level
    )
    city_df = pd.DataFrame([dict(record) for record in city_data], dtype=object)
    # city_df = pd.DataFrame(city_data, dtype=object)

    # Convert to GeoJSON format
    features = []
    for _, row in city_df.iterrows():
        # Parse coordinates from Degree column
        coordinates = [float(row["longitude"]), float(row["latitude"])]

        # Create properties dict excluding certain columns
        columns_to_drop = ["latitude", "longitude", "city"]
        if "country" in row:
            columns_to_drop.append("country")

        row = row.dropna()
        properties = row.drop(columns_to_drop).to_dict()

        if len(row) == 0:
            continue

        feature = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": coordinates},
            "properties": properties,
        }
        features.append(feature)

    # Create GeoJSON structure similar to Google Maps API response
    geojson_data = {"type": "FeatureCollection", "features": features}

    # Generate a unique filename if one isn't provided
    if not filename:
        filename = f"census_{request_location.city_name.lower()}_{data_type}"

    return geojson_data, filename, next_page_token


async def get_commercial_properties_dataset_from_storage(
    filename: str,
    action: str,
    request_location: ReqFetchDataset,
    next_page_token: str,
    data_type: str,
) -> tuple[dict, str, str]:
    """
    Retrieves commercial properties data from database based on the data type requested.
    Returns data in GeoJSON format for consistency with other dataset types.
    """
    data_type = request_location.included_types[0]

    page_number = 0
    if next_page_token:
        page_number = int(next_page_token)

    offset = page_number * DEFAULT_LIMIT

    query = SqlObject.canada_commercial_w_bounding_box_and_property_type

    city_data = await Database.fetch(
        query,
        data_type.replace("_", " "),
        *request_location._bounding_box,
        DEFAULT_LIMIT,
        offset,
    )
    city_df = pd.DataFrame([dict(record) for record in city_data])

    # Convert to GeoJSON format
    features = []
    for _, row in city_df.iterrows():
        # Parse coordinates from Degree column
        coordinates = [float(row["longitude"]), float(row["latitude"])]

        # Create properties dict excluding certain columns
        columns_to_drop = ["latitude", "longitude", "city"]
        if "country" in row:
            columns_to_drop.append("country")
        properties = row.drop(columns_to_drop).to_dict()

        feature = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": coordinates},
            "properties": properties,
        }
        features.append(feature)

    # Create GeoJSON structure similar to Google Maps API response
    geojson_data = {"type": "FeatureCollection", "features": features}

    # Generate a unique filename if one isn't provided
    if not filename:
        filename = f"commercial_canada_{request_location.city_name.lower()}_{data_type}"

    if len(features) < DEFAULT_LIMIT:
        next_page_token = ""
    else:
        next_page_token = str(page_number + 1)

    return geojson_data, filename, next_page_token


async def get_real_estate_dataset_from_storage(
    filename: str,
    action: str,
    request_location: ReqFetchDataset,
    next_page_token: str,
    data_type: str,
) -> tuple[dict, str, str]:
    """
    Retrieves data from storage based on the location request.
    """
    data_type = request_location._included_types
    # TODO at moment the user will only give one category, in the future we should see how to implement this with more
    # realEstateData=(await load_real_estate_categories())
    # filtered_categories = [item for item in realEstateData if item in req.included_types]
    # final_categories = [item for item in filtered_categories if item not in req.excludedTypes]

    page_number = 0
    if next_page_token:
        page_number = int(next_page_token)

    offset = page_number * DEFAULT_LIMIT
    query = SqlObject.saudi_real_estate_w_bounding_box_and_category

    city_data = await Database.fetch(
        query, data_type, *request_location._bounding_box, DEFAULT_LIMIT, offset
    )

    city_df = pd.DataFrame([dict(record) for record in city_data])

    # Convert to GeoJSON format
    features = []
    for _, row in city_df.iterrows():
        # Parse coordinates from Degree column
        coordinates = [float(row["longitude"]), float(row["latitude"])]

        # Create properties dict excluding certain columns
        columns_to_drop = ["latitude", "longitude", "city"]
        if "country" in row:
            columns_to_drop.append("country")
        properties = row.drop(columns_to_drop).to_dict()

        feature = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": coordinates},
            "properties": properties,
        }
        features.append(feature)

    # Create GeoJSON structure similar to Google Maps API response
    geojson_data = {"type": "FeatureCollection", "features": features}

    # Generate a unique filename if one isn't provided
    if not filename:
        filename = f"saudi_real_estate_{request_location.city_name.lower()}_{data_type}"

    if len(features) < DEFAULT_LIMIT:
        next_page_token = ""
    else:
        next_page_token = str(page_number + 1)

    return geojson_data, filename, next_page_token


async def fetch_db_categories_by_lat_lng(bounding_box: list[float]) -> Dict:
    # call db with bounding box
    pass


# Apply the decorator to all functions in this module
apply_decorator_to_module(logger)(__name__)
