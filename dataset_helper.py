import json
<<<<<<< HEAD
=======
import random
>>>>>>> a1cb4af (Modularize the execute_dataset_plan code)
import re
from collections import defaultdict
from backend_common.auth import db

async def read_plan_data(plan_name):
    file_path = (
        f"Backend/layer_category_country_city_matching/full_data_plans/{plan_name}.json"
    )
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


<<<<<<< HEAD
async def excecute_dataset_plan(req, plan_name, layer_id):
=======
async def excecute_dataset_plan(req, plan_name):
>>>>>>> a1cb4af (Modularize the execute_dataset_plan code)
    progress, index = 0, 1
    plan_length = 0
    next_level_batches = set()
    level_results = {}

    while True:
        plan_data = await read_plan_data(plan_name)
        if not plan_data:
            break

        plan_length = len(plan_data) - 1
        current_level_batches = []

        for row in plan_data:
            if "skip" in row:
                continue

            if "end" in row:
                break

            parts = row.split("_")
            lng, lat, radius = float(parts[0]), float(parts[1]), float(parts[2])
            match = re.search(r"circle=([\d.]+)", row)

            if match:
                level = match.group(1)
                level_parts = level.split(".")
                parent_level = (
                    ".".join(level_parts[:-1]) if len(level_parts) > 1 else None
                )

                # Process only if it's a base level or part of the approved hierarchy
                if not next_level_batches or (parent_level in next_level_batches):
                    req.lng = lng
                    req.lat = lat
                    req.radius = radius

                    from data_fetcher import fetch_ggl_nearby
<<<<<<< HEAD
                    dataset, _, _, _ = await fetch_ggl_nearby(req)
                    level_results[level] = dataset

                    if (
                        dataset.get("features")
                        and len(dataset.get("features", "")) >= 20
                    ):
=======
                    dataset = await fetch_ggl_nearby(req)
                    dataset = []
                    level_results[level] = dataset

                    # Simulated result count (for testing)
                    dummy_results = random.randint(15, 25)
                    if dummy_results >= 20:
>>>>>>> a1cb4af (Modularize the execute_dataset_plan code)
                        current_level_batches.append(level)

                    # Re-read the JSON after processing each row
                    plan_data = await read_plan_data(plan_name)

            index += 1
            progress = int((index / plan_length) * 100)
            await db.get_async_client().collection("plan_progress").document(
                plan_name
            ).set({"progress": progress}, merge=True)

<<<<<<< HEAD
            await db.get_async_client().collection("all_user_profiles").document(
                req.user_id
            ).set({"prdcer_lyrs": {layer_id: {"progress": progress}}}, merge=True)

=======
>>>>>>> a1cb4af (Modularize the execute_dataset_plan code)
        # Update next level batches
        next_level_batches.update(current_level_batches)

        # Stop if no more levels qualify
        if not current_level_batches:
            break

    # Ensure final progress update
    await db.get_async_client().collection("plan_progress").document(plan_name).set(
        {"progress": 100}, merge=True
<<<<<<< HEAD
    )
    await db.get_async_client().collection("all_user_profiles").document(
        req.user_id
    ).set({"prdcer_lyrs": {layer_id: {"progress": progress}}}, merge=True)
=======
    )
>>>>>>> a1cb4af (Modularize the execute_dataset_plan code)
