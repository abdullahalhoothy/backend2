import logging
import math
from typing import List, Tuple

import requests
import httpx

from all_types.myapi_dtypes import ReqLocation
from config_factory import get_conf
from logging_wrapper import apply_decorator_to_module

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
CONF = get_conf()



async def fetch_from_google_maps_api(req: ReqLocation):
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": CONF.api_key,
        "X-Goog-FieldMask": CONF.google_fields,
    }
    data ={
            "includedTypes": req.includedTypes,
            "excludedTypes":[],
            "maxResultCount": 10,
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": req.lat,
                        "longitude": req.lng
                    },
                    "radius": req.radius
                }
            }
    }
    client = httpx.AsyncClient()
    response = await client.post(CONF.nearby_search, headers=headers, json=data)
    if response.status_code == 200:
        response_data = response.json()
        results = response_data.get("places", [])
        return results
    else:
        print("Error:", response.status_code)
        return []



# Apply the decorator to all functions in this module
apply_decorator_to_module(logger)(__name__)
