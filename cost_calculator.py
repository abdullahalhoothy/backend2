from all_types.myapi_dtypes import ReqFetchDataset
from all_types.response_dtypes import ResCostEstimate
from storage import use_json
import logging
from backend_common.logging_wrapper import apply_decorator_to_module, preserve_validate_decorator
from backend_common.logging_wrapper import log_and_validate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

COST_PER_1000_CALLS = 40
MAX_CALLS_PER_CITY_PER_CATEGORY = 1000


def estimate_api_calls(categories_data, included_categories, excluded_categories):
    min_calls = max(0.1, min(categories_data.values()))
    included_calls = sum(
        categories_data[cat] for cat in included_categories if cat in categories_data
    )
    excluded_calls = sum(
        categories_data[cat] for cat in excluded_categories if cat in categories_data
    )
    total_calls = included_calls - excluded_calls
    return int(max(min_calls, total_calls) * MAX_CALLS_PER_CITY_PER_CATEGORY)


async def calculate_cost(req: ReqFetchDataset):
    # Load city info from appropriate json file
    file_path = f"Backend/country_info/{req.country_name.lower().replace(' ', '_')}/city_info/{req.city_name.lower().replace(' ', '_')}/ggl_categories.json"
    categories_data = await use_json(file_path, "r")

    # Flatten the nested dictionary
    flattened_categories = {
        subcat: value
        for cat in categories_data
        for subcat, value in categories_data[cat].items()
    }

    api_calls = estimate_api_calls(
        flattened_categories, req.included_categories, req.excluded_categories
    )
    cost = (api_calls / 1000) * COST_PER_1000_CALLS

    return ResCostEstimate(cost=cost, api_calls=api_calls)


# Apply the decorator to all functions in this module
apply_decorator_to_module(logger)(__name__)
