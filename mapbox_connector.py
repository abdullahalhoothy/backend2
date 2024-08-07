from all_types.google_dtypes import GglResponse
from all_types.myapi_dtypes import MapData
from fastapi import HTTPException

class MapBoxConnector:
    @classmethod
    async def ggl_to_boxmap(self, businesses_response) -> MapData:
        features = []

        for business in businesses_response:
            lng = business["geometry"].get('location', {}).get('lng', 0)
            lat = business["geometry"].get('location', {}).get('lat', 0)

            feature = {
                'type': 'Feature',
                'properties': {
                    'name': business.get('name', ''),
                    'rating': business.get('rating', 0),
                    'address': business.get('formatted_address', ''),
                    'phone': business.get('formatted_phone_number', ''),
                    'website': business.get('website', ''),
                    'business_status': business.get('business_status', ''),
                    'user_ratings_total': business.get('user_ratings_total', 0),
                    "heatmap_weight":1
                },
                'geometry': {
                    'type': 'Point',
                    'coordinates': [lng, lat]
                }
            }

            features.append(feature)

        business_data = MapData(
            type='FeatureCollection',
            features=features
        )

        return business_data.model_dump()

    @classmethod
    async def new_ggl_to_boxmap(self, ggl_api_resp) -> MapData:
        features = []

        if ggl_api_resp is None:
            raise HTTPException(
            status_code=404, detail="no data"
        ) 

        for place in ggl_api_resp:
            lng = place.get('location', {}).get('longitude', 0)
            lat = place.get('location', {}).get('latitude', 0)

            feature = {
                'type': 'Feature',
                'properties': {
                    'name': place.get('displayName', '').get("text",""),
                    'rating': place.get('rating', ''),
                    'address': place.get('formattedAddress', ''),
                    'phone': place.get('internationalPhoneNumber',""),
                    'types': place.get('types', ''),
                    'priceLevel': place.get('priceLevel', ''),
                    'primaryType': place.get('primaryType', ''),
                    'user_ratings_total': place.get('userRatingCount', ''),
                    "heatmap_weight":1
                    
                },
                'geometry': {
                    'type': 'Point',
                    'coordinates': [lng, lat]
                }
            }

            features.append(feature)

        business_data = MapData(
            type='FeatureCollection',
            features=features
        )

        return business_data.model_dump()









