import aiohttp
import logging
from typing import List, Dict, Any, Tuple, Optional
import json
from all_types.request_dtypes import ReqStreeViewCheck
import hashlib
from backend_common.database import Database
from sql_object import SqlObject
from backend_common.logging_wrapper import apply_decorator_to_module

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def _get_test_data_for_get_call(ggl_api_url: str, headers: dict) -> dict:
    """Get test data for GET API calls (place details)"""
    # Extract place_id from URL for place details calls
    # URL format: https://places.googleapis.com/v1/places/{place_id}
    if "/places/" in ggl_api_url:
        place_id = ggl_api_url.split("/places/")[-1].split("?")[0]
        filename = f"test_place_details_{place_id}"
    else:
        # Generate filename based on URL hash for other GET calls
        url_hash = hashlib.md5(ggl_api_url.encode()).hexdigest()[:12]
        filename = f"test_get_call_{url_hash}"

    try:
        result = await Database.fetchrow(SqlObject.load_dataset, filename)
        if result and result["response_data"]:
            logger.info(f"Found test data for GET call: {filename}")
            return json.loads(result["response_data"])
        else:
            logger.warning(f"No test data found for GET call: {filename}")
            return {}
    except Exception as e:
        logger.error(f"Error loading test data for GET call: {e}")
        return {}


async def _get_test_data_for_post_call(
    ggl_api_url: str, headers: dict, data: dict
) -> list:
    """Get test data for POST API calls (nearby search, text search)"""
    # Generate filename based on request parameters
    if "textQuery" in data:
        # Text search
        text_query = data.get("textQuery", "")
        location = (
            data.get("locationBias", {}).get("circle", {}).get("center", {})
        )
        radius = (
            data.get("locationBias", {}).get("circle", {}).get("radius", 1500)
        )
        lat = location.get("latitude", 0)
        lng = location.get("longitude", 0)

        filename = (
            f"test_text_search_{lat}_{lng}_{radius}_{text_query}".replace(
                " ", "_"
            )
        )

    elif "includedTypes" in data or "excludedTypes" in data:
        # Category search
        included_types = data.get("includedTypes", [])
        excluded_types = data.get("excludedTypes", [])
        location = (
            data.get("locationRestriction", {})
            .get("circle", {})
            .get("center", {})
        )
        radius = (
            data.get("locationRestriction", {})
            .get("circle", {})
            .get("radius", 1500)
        )
        lat = location.get("latitude", 0)
        lng = location.get("longitude", 0)

        included_str = "_".join(sorted(included_types))
        excluded_str = "_".join(sorted(excluded_types))
        filename = f"test_category_search_{lat}_{lng}_{radius}_inc_{included_str}_exc_{excluded_str}"

    else:
        # Fallback: generate filename based on data hash
        data_hash = hashlib.md5(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()[:12]
        filename = f"test_post_call_{data_hash}"

    # Clean filename (remove invalid characters and limit length)
    filename = "".join(c for c in filename if c.isalnum() or c in "._-")[:100]

    try:
        result = await Database.fetchrow(SqlObject.load_dataset, filename)
        if result and result["response_data"]:
            logger.info(f"Found test data for POST call: {filename}")
            response_data = json.loads(result["response_data"])
            # Return the places array for consistency with Google API response
            return (
                response_data.get("places", [])
                if isinstance(response_data, dict)
                else response_data
            )
        else:
            logger.warning(f"No test data found for POST call: {filename}")
            return []
    except Exception as e:
        logger.error(f"Error loading test data for POST call: {e}")
        return []


async def _get_test_data_for_street_view(req: ReqStreeViewCheck) -> dict:
    """Get test data for Street View API calls"""
    # Generate filename based on coordinates
    filename = f"test_street_view_{req.lat}_{req.lng}".replace(".", "_")

    try:
        result = await Database.fetchrow(SqlObject.load_dataset, filename)
        if result and result["response_data"]:
            logger.info(f"Found test data for Street View: {filename}")
            return json.loads(result["response_data"])
        else:
            logger.warning(f"No test data found for Street View: {filename}")
            # Return default response indicating street view is available
            return {"has_street_view": True}
    except Exception as e:
        logger.error(f"Error loading test data for Street View: {e}")
        return {"has_street_view": False}



# Apply the decorator to all functions in this module
apply_decorator_to_module(logger)(__name__)
