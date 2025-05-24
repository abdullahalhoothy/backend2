from datetime import datetime
import json
import random
import re
from collections import defaultdict
from backend_common.auth import firebase_db
from google_api_connector import fetch_ggl_nearby
from all_types.request_dtypes import ReqFetchDataset
import logging
from firebase_admin import firestore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def read_plan_data(plan_name):
    file_path = f"Backend/layer_category_country_city_matching/full_data_plans/{plan_name}.json"
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        return []


async def create_batches(plan_data):
    batches = defaultdict(list)

    for item in plan_data:
        match = re.search(r"circle=([\d.]+)", item)
        if match:
            circle_value = match.group(1)
            level = circle_value.count(".") + 1
            batches[level].append(item)

    # Creating batches of 5 within each level
    final_batches = []
    for level, items in batches.items():
        for i in range(0, len(items), 5):
            final_batches.append(items[i : i + 5])

    return final_batches


async def excecute_dataset_plan(
    req: ReqFetchDataset, plan_name, layer_id, next_page_token
):

    progress = 0
    count_calls = 1
    plan_length = 0
    next_plan_index = 1

    while True:
        try:
            plan_data = await read_plan_data(plan_name)
            plan_length = len(plan_data) - 1
            previous_level = 0

            # Safety check for index
            if next_plan_index >= len(plan_data):
                logger.error(
                    f"Plan index {next_plan_index} out of bounds (max: {len(plan_data)-1})"
                )
                break

            search_item = plan_data[next_plan_index]
            if "skip" in search_item:
                next_plan_index += 1
                continue

            if "end of search plan" in search_item:
                break

            match = re.search(r"circle=([\d.]+)", search_item)

            level = match.group(1)
            level_parts = level.split(".")
            current_level = len(level_parts)

            req.page_token = next_page_token
            (
                _,
                _,
                next_page_token,
                _,
                next_plan_index,
            ) = await fetch_ggl_nearby(req)

            if next_page_token == "":
                break

            if current_level != previous_level:
                # Re-read plan after each 5 calls
                plan_data = await read_plan_data(plan_name)
                previous_level = current_level

            count_calls += 1
            progress = int((next_plan_index / plan_length) * 100)
            await firebase_db.get_async_client().collection("plan_progress").document(
                plan_name
            ).set({
                "progress": progress, 
                "api_call": count_calls,
                "last_updated": firestore.SERVER_TIMESTAMP
            }, merge=True)
        except Exception as e:
            logger.error(f"Error in execution loop: {str(e)}", exc_info=True)
            break
        
    # Ensure final progress update
    await firebase_db.get_async_client().collection("plan_progress").document(
        plan_name
    ).set({"progress": 100, "completed_at": datetime.now()}, merge=True)
    await firebase_db.get_async_client().collection("all_user_profiles").document(
        req.user_id
    ).set({"prdcer_lyrs": {layer_id: {"progress": progress}}}, merge=True)
