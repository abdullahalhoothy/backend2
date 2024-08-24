import logging
import uuid
from datetime import datetime, date
from typing import Any, Dict, Tuple, Optional, Union, List
import json
import os
import asyncio
import aiofiles
from contextlib import asynccontextmanager
from fastapi import HTTPException, status
from pydantic import BaseModel

from all_types.myapi_dtypes import ReqLocation, ReqFetchDataset,ReqRealEstate
from config_factory import get_conf
from logging_wrapper import apply_decorator_to_module

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
USERS_INFO_PATH = "Backend/users_info.json"
RIYADH_VILLA_ALLROOMS= "Backend/riyadh_villa_allrooms.json" # to be change to real estate id needed
REAL_ESTATE_CATEGORIES_PATH="Backend/real_estate_categories.json"

CONF = get_conf()
os.makedirs(STORAGE_DIR, exist_ok=True)


class FileLock:
    def __init__(self):
        self.locks = {}

    @asynccontextmanager
    async def acquire(self, filename):
        if filename not in self.locks:
            self.locks[filename] = asyncio.Lock()
        async with self.locks[filename]:
            yield

file_lock_manager = FileLock()


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


def make_ggl_dataset_cord_filename(lng: str, lat: str, radius: str):
    return f"{lng}_{lat}_{radius}"


def make_ggl_layer_filename(req: ReqFetchDataset) -> str:
    type_string = make_include_exclude_name(req.includedTypes, req.excludedTypes)
    tcc_string = f"{type_string}_{req.dataset_country}_{req.dataset_city}"
    return tcc_string


def make_ggl_dataset_filename(req) -> str:
    cord_string = make_ggl_dataset_cord_filename(req.lng, req.lat, req.radius)
    type_string = make_include_exclude_name(req.includedTypes, req.excludedTypes)
    try:
        name = f"{cord_string}_{type_string}_token={req.page_token}"
        if req.text_search != "" and req.text_search is not None:
            name = name + f"_text_search:{req.text_search}_"
        return name
    except AttributeError as e:
        raise ValueError(f"Invalid location request object: {str(e)}")


async def search_metastore_for_string(string_search: str) -> Optional[Dict]:
    """
    Searches the metastore for a given string and returns the corresponding data if found.
    """
    meta_file_path = os.path.join(METASTORE_PATH, string_search)
    try:
        if os.path.exists(meta_file_path):
            with open(meta_file_path, "r") as f:
                return json.load(f)
        return None
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error parsing metastore file",
        )
    except IOError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error reading metastore file",
        )


def load_dataset_layer_matching() -> Dict:
    """ """
    try:
        with open(DATASET_LAYER_MATCHING_PATH, "r") as f:
            dataset_layer_matching = json.load(f)
        return dataset_layer_matching
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset layer matching file not found",
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error parsing dataset layer matching file",
        )


def fetch_dataset_id(
        lyr_id: str, dataset_layer_matching: Dict = None
) -> Tuple[str, Dict]:
    """
    Searches for the dataset ID associated with a given layer ID. This function
    reads the dataset-layer matching file and iterates through it to find the
    corresponding dataset for a given layer.
    """
    if dataset_layer_matching is None:
        dataset_layer_matching = load_dataset_layer_matching()

    for d_id, dataset_info in dataset_layer_matching.items():
        if lyr_id in dataset_info["prdcer_lyrs"]:
            return d_id, dataset_info
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found for this layer"
    )


def fetch_layer_owner(prdcer_lyr_id: str) -> str:
    """
    Fetches the owner of a layer based on the producer layer ID.
    """
    try:
        with open(USER_LAYER_MATCHING_PATH, "r") as f:
            user_layer_matching = json.load(f)
        layer_owner_id = user_layer_matching.get(prdcer_lyr_id)
        if not layer_owner_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Layer owner not found"
            )
        return layer_owner_id
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User layer matching file not found",
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error parsing user layer matching file",
        )


def load_user_profile(user_id: str) -> Dict:
    """
    Loads user data from a file based on the user ID.
    """
    user_file_path = os.path.join(USERS_PATH, f"user_{user_id}.json")
    try:
        with open(user_file_path, "r") as f:
            user_data = json.load(f)
        return user_data
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User profile does not exist"
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error parsing user profile",
        )


def update_dataset_layer_matching(
        prdcer_lyr_id: str, bknd_dataset_id: str, records_count: int = 9191919
):
    try:
        if os.path.exists(DATASET_LAYER_MATCHING_PATH):
            with open(DATASET_LAYER_MATCHING_PATH, "r") as f:
                dataset_layer_matching = json.load(f)
        else:
            dataset_layer_matching = {}

        if bknd_dataset_id not in dataset_layer_matching:
            dataset_layer_matching[bknd_dataset_id] = {
                "records_count": records_count,
                "prdcer_lyrs": [],
            }

        if prdcer_lyr_id not in dataset_layer_matching[bknd_dataset_id]["prdcer_lyrs"]:
            dataset_layer_matching[bknd_dataset_id]["prdcer_lyrs"].append(prdcer_lyr_id)

        dataset_layer_matching[bknd_dataset_id]["records_count"] = records_count

        with open(DATASET_LAYER_MATCHING_PATH, "w") as f:
            json.dump(dataset_layer_matching, f, indent=2)
    except IOError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating dataset layer matching",
        )


def update_user_layer_matching(layer_id: str, layer_owner_id: str):
    try:
        with open(USER_LAYER_MATCHING_PATH, "r+") as f:
            user_layer_matching = json.load(f)
            user_layer_matching[layer_id] = layer_owner_id
            f.seek(0)
            json.dump(user_layer_matching, f, indent=2)
            f.truncate()
    except IOError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating user layer matching",
        )


def update_user_profile(user_id: str, user_data: Dict):
    user_file_path = os.path.join(USERS_PATH, f"user_{user_id}.json")
    try:
        with open(user_file_path, "w") as f:
            json.dump(user_data, f, indent=2)
    except IOError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating user profile",
        )


def fetch_user_layers(user_id: str) -> Dict[str, Any]:
    try:
        user_data = load_user_profile(user_id)
        user_layers = user_data.get("prdcer", {}).get("prdcer_lyrs", {})
        return user_layers
    except FileNotFoundError as fnfe:
        logger.error(f"User layers not found for user_id: {user_id}")
        raise HTTPException(status_code=404, detail="User layers not found") from fnfe


def fetch_user_catalogs(user_id: str) -> Dict[str, Any]:
    try:
        user_data = load_user_profile(user_id)
        user_catalogs = user_data.get("prdcer", {}).get("prdcer_ctlgs", {})
        return user_catalogs
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user catalogs: {str(e)}",
        )


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
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error parsing store catalogs file",
        )


def update_metastore(ccc_filename: str, bknd_dataset_id: str):
    """Update the metastore with the new layer information"""
    if bknd_dataset_id is not None:
        try:
            metastore_data = {
                "bknd_dataset_id": bknd_dataset_id,
                "created_at": datetime.now().isoformat(),
            }
            with open(f"{METASTORE_PATH}/{ccc_filename}", "w") as f:
                json.dump(metastore_data, f)
        except IOError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error updating metastore",
            )


def get_country_code(country_name: str) -> str:
    country_codes = {"United Arab Emirates": "AE", "Saudi Arabia": "SA", "Canada": "CA"}
    return country_codes.get(country_name, "")


def load_country_city():
    data = {
        "United Arab Emirates": [
            {"name": "Dubai", "lat": 25.2048, "lng": 55.2708},
            {"name": "Abu Dhabi", "lat": 24.4539, "lng": 54.3773},
            {"name": "Sharjah", "lat": 25.3573, "lng": 55.4033},
        ],
        "Saudi Arabia": [
            {"name": "Riyadh", "lat": 24.7136, "lng": 46.6753},
            {"name": "Jeddah", "lat": 21.5433, "lng": 39.1728},
            {"name": "Mecca", "lat": 21.4225, "lng": 39.8262},
        ],
        "Canada": [
            {"name": "Toronto", "lat": 43.6532, "lng": -79.3832},
            {"name": "Vancouver", "lat": 49.2827, "lng": -123.1207},
            {"name": "Montreal", "lat": 45.5017, "lng": -73.5673},
        ],
    }

    return data


def load_google_categories():
    try:
        with open("Backend/google_categories.json", "r") as f:
            categories = json.load(f)
        return categories
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Categories file not found"
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error parsing categories file",
        )

async def load_real_estate_categories() ->dict:
    file_path = REAL_ESTATE_CATEGORIES_PATH
    json_data = await use_json(file_path, "r")
    return json_data


def generate_layer_id() -> str:
    return "l" + str(uuid.uuid4())


async def use_json(file_path: str, mode: str, json_content: dict = None) -> Optional[dict]:
    async with file_lock_manager.acquire(file_path):
        if mode == "w":
            try:
                async with aiofiles.open(file_path, mode='w') as file:
                    await file.write(json.dumps(json_content, indent=2))
            except IOError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error writing data file",
                )

        elif mode == "r":
            try:
                if os.path.exists(file_path):
                    async with aiofiles.open(file_path, mode='r') as file:
                        content = await file.read()
                        return json.loads(content)
                return None
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error parsing data file",
                )
            except IOError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error reading data file",
                )
        else:
            raise ValueError("Invalid mode. Use 'r' for read or 'w' for write.")


async def save_plan(plan_name, plan):
    file_path = (
        f"Backend/layer_category_country_city_matching/full_data_plans/{plan_name}.json"
    )
    await use_json(file_path, "w", plan)


async def get_plan(plan_name):
    file_path = (
        f"Backend/layer_category_country_city_matching/full_data_plans/{plan_name}.json"
    )
    # use json file
    json_content = await use_json(file_path, "r")
    return json_content


async def store_ggl_data_resp(req: ReqLocation, dataset: Dict) -> str:
    """
    Stores data in a file based on the location request.
    """
    # TODO add time stamp to the dataset , when it was retrived
    filename = make_ggl_dataset_filename(req)
    file_path = f"{STORAGE_DIR}/{filename}.json"
    await use_json(file_path, "w", dataset)

    return filename


async def get_dataset_from_storage(req: ReqLocation) -> tuple[Optional[Dict], Optional[str]]:
    """
    Retrieves data from storage based on the location request.
    """
    filename = make_ggl_dataset_filename(req)
    file_path = f"{STORAGE_DIR}/{filename}.json"

    json_data = await use_json(file_path, "r")
    if json_data is not None:
        return json_data, filename
    return None, None


async def create_real_estate_plan(req: ReqRealEstate) -> list[str]:
    country= req.country_name.lower().replace(" ","_")
    folder_path = f"{BACKEND_DIR}/{country}/{req.city_name.lower()}/{req.includedTypes[0]}"
    files = os.listdir(folder_path)
    files = [file.split(".json")[0] for file in files]
    return files


async def get_real_estate_dataset_from_storage(req: ReqRealEstate, filename: str,action:str) -> tuple[dict, str]:
    """
    Retrieves data from storage based on the location request.
    """
    # TODO at moment the user will only give one category, in the future we should see how to implement this with more
    # realEstateData=(await load_real_estate_categories())
    # filtered_categories = [item for item in realEstateData if item in req.includedTypes]
    # final_categories = [item for item in filtered_categories if item not in req.excludedTypes]

    country= req.country_name.lower().replace(" ","_")
    folder_path = f"{BACKEND_DIR}/{country}/{req.city_name.lower()}/{req.includedTypes[0]}"
    if action == "full data":
        file_path = f"{folder_path}/{filename}.json"
    else:
        files = os.listdir(folder_path)
        file_path = f'{folder_path}/{files[0]}'
        filename = files[0].split(".json")[0]
    json_data = await use_json(file_path, "r")    
    if json_data is not None:
        return json_data, filename
    return None, None


async def load_dataset(dataset_id: str) -> Dict:
    """
    Loads a dataset from file based on its ID.
    """
    dataset_filepath = os.path.join(STORAGE_DIR, f"{dataset_id}.json")
    json_content = await use_json(dataset_filepath, "r")
    return json_content


async def save_to_json_file(folder_name:str,file_name:str, data:dict)->None:
    if not os.path.exists(f"Backend/{folder_name}"):
        os.makedirs(f"Backend/{folder_name}")

    file_path = f"Backend/{folder_name}/{file_name}.json"

    json_content = await use_json(file_path, "r")
    return json_content

# Apply the decorator to all functions in this module
apply_decorator_to_module(logger)(__name__)
