from datetime import datetime
import json
import random
import re
from collections import defaultdict
from backend_common.auth import db
from google_api_connector import fetch_ggl_nearby
from all_types.myapi_dtypes import ReqFetchDataset


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
    index = 1
    plan_length = 0

    while True:
        plan_data = await read_plan_data(plan_name)
        if not plan_data:
            break

        plan_length = len(plan_data) - 1
        previous_level = 0

        for row in plan_data:
            if "skip" in row:
                continue

            if "end of search plan" in row:
                break

            match = re.search(r"circle=([\d.]+)", row)

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

            if current_level != previous_level:
                # Re-read plan after each 5 calls
                plan_data = await read_plan_data(plan_name)
                previous_level = current_level

            index += 1
            progress = int((next_plan_index / plan_length) * 100)
            await db.get_async_client().collection("plan_progress").document(
                plan_name
            ).set({"progress": progress, "api_call": index}, merge=True)

    # Ensure final progress update
    await db.get_async_client().collection("plan_progress").document(
        plan_name
    ).set({"progress": 100, "completed_at": datetime.now()}, merge=True)
    await db.get_async_client().collection("all_user_profiles").document(
        req.user_id
    ).set({"prdcer_lyrs": {layer_id: {"progress": progress}}}, merge=True)
