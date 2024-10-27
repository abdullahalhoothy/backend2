import aiohttp
import logging
import math
from typing import List, Tuple, Dict

from fastapi import HTTPException
import requests

from all_types.myapi_dtypes import ReqLocation, ReqStreeViewCheck
from backend_common.request_processor import output_update_with_req_msg
from config_factory import CONF
from backend_common.logging_wrapper import apply_decorator_to_module

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)





async def fetch_from_google_maps_api(req: ReqLocation):


    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": CONF.api_key,
        "X-Goog-FieldMask": CONF.google_fields,
    }
    data = {
        "includedTypes": [req.includedTypes],
        "excludedTypes": [req.excludedTypes],
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": req.lat,
                    "longitude": req.lng
                },
                "radius": req.radius
            }
        },
    }

    response = requests.post(CONF.nearby_search, headers=headers, json=data)
    if response.status_code == 200:
        response_data = response.json()
        results = response_data.get("places", [])

        return results, ""
    else:
        print("Error:", response.status_code)
        return [], None


@output_update_with_req_msg
async def check_street_view_availability(req: ReqStreeViewCheck) -> Dict[str, bool]:
    url = f"https://maps.googleapis.com/maps/api/streetview?return_error_code=true&size=600x300&location={req.lat},{req.lng}&heading=151.78&pitch=-0.76&key={CONF.api_key}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return {"has_street_view": True}
            else:
                raise HTTPException(
                    status_code=response.status,
                    detail="Error checking Street View availability",
                )


# Apply the decorator to all functions in this module
apply_decorator_to_module(logger)(__name__)
