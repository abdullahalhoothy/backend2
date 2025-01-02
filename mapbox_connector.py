from all_types.google_dtypes import GglResponse
from all_types.response_dtypes import MapData
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

class MapBoxConnector:

    @classmethod
    def assign_point_properties(cls, place):
        # Extract coordinates
        coordinates = place.get("geometry", {}).get("coordinates", [0, 0])
        lng, lat = coordinates if len(coordinates) == 2 else (0, 0)

        # Extract properties
        properties = place.get("properties", {})
        
        return {
            "type": "Feature",
            "properties": {
                "name": properties.get("name", ""),
                "rating": properties.get("rating", ""),
                "address": properties.get("address", ""),
                "phone": properties.get("phone", ""),
                "types": properties.get("types", []),
                "priceLevel": properties.get("priceLevel", ""),
                "primaryType": properties.get("primaryType", ""),
                "user_ratings_total": properties.get("user_ratings_total", ""),
                "heatmap_weight": properties.get("heatmap_weight", 1),
            },
            "geometry": {"type": "Point", "coordinates": [lng, lat]},
        }


    @classmethod
    async def new_ggl_to_boxmap(cls, ggl_api_resp) -> MapData:
        if ggl_api_resp is None:
            raise HTTPException(status_code=404, detail="no data")
        
        features = [cls.assign_point_properties(place) for place in ggl_api_resp]
        
        # Get property keys from the first feature if features exist
        feature_properties = []
        if features:
            # Extract all property keys from the first feature's properties
            feature_properties = list(features[0]["properties"].keys())
        
        business_data = MapData(
            type="FeatureCollection", 
            features=features, 
            properties=feature_properties
        )
        return business_data.model_dump()