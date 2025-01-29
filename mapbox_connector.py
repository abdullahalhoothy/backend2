from all_types.google_dtypes import GglResponse
from all_types.response_dtypes import MapData
from fastapi import HTTPException


class MapBoxConnector:

    @classmethod
    def assign_point_properties(cls, place):
        lng = place.get("location", {}).get("longitude", 0)
        lat = place.get("location", {}).get("latitude", 0)
        return {
            "type": "Feature",
            "properties": {
                "name": place.get("displayName", {}).get("text", ""),
                "rating": place.get("rating", ""),
                "address": place.get("formattedAddress", ""),
                "phone": place.get("internationalPhoneNumber", ""),
                "types": place.get("types", ""),
                "priceLevel": place.get("priceLevel", ""),
                "primaryType": place.get("primaryType", ""),
                "user_ratings_total": place.get("userRatingCount", ""),
                "heatmap_weight": 1,
            },
            "geometry": {"type": "Point", "coordinates": [lng, lat]},
        }

    @classmethod
    async def new_ggl_to_boxmap(cls, ggl_api_resp) -> MapData:
        if not ggl_api_resp:  # This will handle None, empty string, or empty list
            return MapData(
                type="FeatureCollection",
                features=[],
                properties=[]
            ).model_dump()
        
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