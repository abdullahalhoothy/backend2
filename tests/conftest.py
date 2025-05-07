import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi_app import app


pytest_plugins = 'pytest_asyncio'

@pytest.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as ac:
        with patch("backend_common.auth.JWTBearer.__call__", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = True
            yield ac


# @pytest.fixture
# async def get_auth_header(async_client):  # TODO
#     login_data = {"username": "testuser", "password": "securepassword"}
#     response = await async_client.post("/login", data=login_data)
#     assert response.status_code == 200
#     return {"Authorization": f"Bearer {response.json().get("access_token")}"}


# Add test data fixtures
@pytest.fixture
def req_fetch_dataset_real_estate():
    return {
        "message": "Request from frontend",
        "request_info": {},
        "request_body": {
            "country_name": "Saudi Arabia",  # Changed from UAE to match real estate data
            "city_name": "Riyadh",
            "boolean_query": "apartment_for_rent",
            "layerId": "",
            "layer_name": "Saudi Arabia Riyadh apartments",
            "action": "sample",
            "search_type": "category_search",
            "text_search": "",
            "page_token": "",
            "user_id": "qnVMpp2NbpZArKuJuPL0r9luGP13",
            "zoom_level": 4
        }
    }


@pytest.fixture
def req_fetch_dataset_pai():
    return {
        "message": "Request from frontend",
        "request_info": {},
        "request_body": {
            "country_name": "Saudi Arabia",  # Changed from UAE to match real estate data
            "city_name": "Riyadh",
            "boolean_query": "TotalPopulation",
            "layerId": "",
            "layer_name": "Saudi Arabia Riyadh apartments",
            "action": "sample",
            "search_type": "category_search",
            "text_search": "",
            "page_token": "",
            "user_id": "qnVMpp2NbpZArKuJuPL0r9luGP13",
            "zoom_level": 4
        }
    }


@pytest.fixture
def req_fetch_dataset_commercial():
    return {
        "message": "Request from frontend",
        "request_info": {},
        "request_body": {
            "country_name": "Canada",  # Changed from UAE to match real estate data
            "city_name": "Riyadh",
            "boolean_query": "business_for_rent",
            "layerId": "",
            "layer_name": "Saudi Arabia Riyadh apartments",
            "action": "sample",
            "search_type": "category_search",
            "text_search": "",
            "page_token": "",
            "user_id": "qnVMpp2NbpZArKuJuPL0r9luGP13",
            "zoom_level": 4
        }
    }


@pytest.fixture
def req_fetch_dataset_google_category_search():
    return {
   "message":"Request from frontend",
   "request_info":{
   },
   "request_body":{
      "country_name":"United Arab Emirates",
      "city_name":"Dubai",
      "boolean_query":"car_dealer OR car_rental",
      "layerId":"",
      "layer_name":"United Arab Emirates Dubai car dealer + car rental",
      "action":"sample",
      "search_type":"category_search",
      "text_search":"",
      "page_token":"",
      "user_id":"qnVMpp2NbpZArKuJuPL0r9luGP13",
      "zoom_level":4
   }
}

@pytest.fixture
def stripe_customer():
    return {'id': 'cus_Rp2YvT2OyJh5hR'}


@pytest.fixture
def sample_real_estate_response():
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [46.6753, 24.7136]
                },
                "properties": {
                    "price": 500000,
                    "url": "http://example.com",
                    "city": "Riyadh",
                    "category": "apartment_for_rent"
                }
            }
        ]
    }


@pytest.fixture
def sample_google_category_search_response():
    return {
        'type': 'FeatureCollection',
        'features': [
            {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.215655, 25.131934]}, 'properties': {'id': 'ChIJ9S4BtZFpXz4RmXiYRUQjUZk', 'name': 'Jetour Dubai Showroom - Al Quoz', 'phone': '', 'types': ['car_dealer', 'store', 'point_of_interest', 'establishment'], 'rating': 4.8, 'address': 'Warehouse 04 - القوز - منطقة القوز الصناعية 3 - دبي - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_dealer', 'heatmap_weight': 1, 'popularity_score': 250.0, 'user_ratings_total': 3072, 'popularity_score_category': 'Very High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.2457717, 25.174815199999998]}, 'properties': {'id': 'ChIJ3Uctl-lpXz4RhhyZW3iwkXI', 'name': 'BMW | AGMC', 'phone': '', 'types': ['car_dealer', 'point_of_interest', 'store', 'establishment'], 'rating': 4.2, 'address': 'Sheikh Zayed Rd - Al Quoz - Al Quoz 1 - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_dealer', 'heatmap_weight': 1, 'popularity_score': 250.0, 'user_ratings_total': 2907, 'popularity_score_category': 'Very High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.239484, 25.1682983]}, 'properties': {'id': 'ChIJ1aa4uMJpXz4Re0u3zU5aAZI', 'name': 'Toyota Showroom - Sheikh Zayed Road Al Quoz 1', 'phone': '', 'types': ['car_dealer', 'point_of_interest', 'store', 'establishment'], 'rating': 4, 'address': 'Sheikh Zayed Road - Al Quoz - Al Quoz 1 - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_dealer', 'heatmap_weight': 1, 'popularity_score': 250.0, 'user_ratings_total': 2346, 'popularity_score_category': 'Very High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.3972725, 25.3152486]}, 'properties': {'id': 'ChIJndylsPhbXz4Rjz19bS3iogI', 'name': 'Marhaba Auctions - Main Branch', 'phone': '', 'types': ['car_dealer', 'store', 'point_of_interest', 'establishment'], 'rating': 4.1, 'address': '247 First Industrial St - Industrial Area 2 - Industrial Area - Sharjah - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_dealer', 'heatmap_weight': 1, 'popularity_score': 250.0, 'user_ratings_total': 1629, 'popularity_score_category': 'Very High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.4013127, 25.3178663]}, 'properties': {'id': 'ChIJYzKbch5bXz4RQGlYjOrIL5I', 'name': 'Al Qaryah Auctions', 'phone': '', 'types': ['market', 'car_dealer', 'store', 'point_of_interest', 'establishment'], 'rating': 4.3, 'address': 'First Industrial St - Industrial Area 2 - Industrial Area - Sharjah - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_dealer', 'heatmap_weight': 1, 'popularity_score': 250.0, 'user_ratings_total': 1629, 'popularity_score_category': 'Very High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.11249480000001, 24.984491199999997]}, 'properties': {'id': 'ChIJ5ccYx5cNXz4RPwI8dGR_lV4', 'name': 'CARS24 MRL (Test Drive & Service Centre In Dubai) | Used cars in UAE, Servicing in Dubai', 'phone': '', 'types': ['car_repair', 'car_dealer', 'store', 'point_of_interest', 'establishment'], 'rating': 4.5, 'address': 'Jebel Ali Industrial Area - Jabal Ali Industrial First - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_dealer', 'heatmap_weight': 1, 'popularity_score': 250.0, 'user_ratings_total': 9315, 'popularity_score_category': 'Very High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.3737011, 25.1699996]}, 'properties': {'id': 'ChIJs-ek8vZnXz4R4nvuZRcNpcs', 'name': 'Ryan Motors FZE', 'phone': '', 'types': ['car_dealer', 'store', 'point_of_interest', 'establishment'], 'rating': 4, 'address': 'Showroom No. 240, Ras Al Khor, Al Aweer Ducamz - منطقة رأس الخور الصناعية - منطقة رأس الخور الصناعية - ٣ - دبي - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_dealer', 'heatmap_weight': 1, 'popularity_score': 250.0, 'user_ratings_total': 173, 'popularity_score_category': 'Very High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.48196180000001, 25.3508302]}, 'properties': {'id': 'ChIJnSK0zaRYXz4RyHhzGmjM6vc', 'name': 'سوق الحراج للسيارات الشارقة', 'phone': '', 'types': ['market', 'car_dealer', 'car_repair', 'store', 'point_of_interest', 'establishment'], 'rating': 3.9, 'address': 'Sheikh Muhammed Bin Zayed Rd, Souq Al Haraj - Al Ruqa Al Hamra - Sharjah - United Arab Emirates', 'priceLevel': '', 'primaryType': '', 'heatmap_weight': 1, 'popularity_score': 250.0, 'user_ratings_total': 845, 'popularity_score_category': 'Very High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.209646299999996, 25.127500899999998]}, 'properties': {'id': 'ChIJD_JFFKZrXz4RUQ23r7YmwRY', 'name': 'Tesla Centre Dubai Sheikh Zayed Road', 'phone': '', 'types': ['car_repair', 'car_dealer', 'store', 'point_of_interest', 'establishment'], 'rating': 3.4, 'address': '751 Sheikh Zayed Rd - Al Quoz - Al Quoz Industrial Area 3 - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_dealer', 'heatmap_weight': 1, 'popularity_score': 250.0, 'user_ratings_total': 749, 'popularity_score_category': 'Very High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.2432936, 25.172268100000004]}, 'properties': {'id': 'ChIJjaVPGmZpXz4RlutPNS17nck', 'name': 'Kia Showroom - Sheikh Zayed Road "The Move" معرض كيا شارع الشيخ زايد', 'phone': '', 'types': ['car_dealer', 'point_of_interest', 'store', 'establishment'], 'rating': 4.1, 'address': 'Sheikh Zayed Rd - Al Quoz - Al Quoz 1 - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_dealer', 'heatmap_weight': 1, 'popularity_score': 250.0, 'user_ratings_total': 560, 'popularity_score_category': 'Very High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.36702, 25.168754399999997]}, 'properties': {'id': 'ChIJYZ9CzORmXz4RhxxiZd3ZMXw', 'name': 'Al Aweer Auto Market', 'phone': '', 'types': ['car_dealer', 'store', 'point_of_interest', 'establishment'], 'rating': 4, 'address': 'Ras alkhor auto market - Nad Al Hamar Rd - Ras Al Khor Industrial Area - Ras Al Khor Industrial Area 3 - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_dealer', 'heatmap_weight': 1, 'popularity_score': 250.0, 'user_ratings_total': 1241, 'popularity_score_category': 'Very High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.2072461, 25.1186337]}, 'properties': {'id': 'ChIJrx2Or8FrXz4RiYWRgp_AiGM', 'name': 'The Iridium Building', 'phone': '', 'types': ['dental_clinic', 'fitness_center', 'gym', 'beauty_salon', 'general_contractor', 'consultant', 'car_dealer', 'store', 'sports_activity_location', 'point_of_interest', 'health', 'establishment'], 'rating': 4.1, 'address': 'البرشاء1, شارع أم سقيم - Um Suqeim Street - Al Barsha - Al Barsha 1 - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': '', 'heatmap_weight': 1, 'popularity_score': 250.0, 'user_ratings_total': 304, 'popularity_score_category': 'Very High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.2199215, 25.14134]}, 'properties': {'id': 'ChIJQ6pE0aprXz4Ray3xtVDeB0Q', 'name': 'Al Tayer Motors, Ford Showroom, Sheikh Zayed Road', 'phone': '', 'types': ['car_dealer', 'store', 'point_of_interest', 'establishment'], 'rating': 4.2, 'address': '697 Sheikh Zayed Rd - Al Quoz - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_dealer', 'heatmap_weight': 1, 'popularity_score': 250.0, 'user_ratings_total': 555, 'popularity_score_category': 'Very High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.36481380000001, 25.1688904]}, 'properties': {'id': 'ChIJsXeWJAJnXz4R279L4QcolrA', 'name': 'Emirates Auction الامارات للمزادات', 'phone': '', 'types': ['car_dealer', 'store', 'point_of_interest', 'establishment'], 'rating': 4.3, 'address': 'Al Manama St - opp. Used Cars Market - Ras Al Khor Industrial Area - Ras Al Khor Industrial Area 2 - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': '', 'heatmap_weight': 1, 'popularity_score': 250.0, 'user_ratings_total': 2057, 'popularity_score_category': 'Very High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.2477397, 25.1771507]}, 'properties': {'id': 'ChIJgzCF101pXz4RiM_nyFseltI', 'name': 'F1rst Motors', 'phone': '', 'types': ['car_dealer', 'point_of_interest', 'store', 'establishment'], 'rating': 4.9, 'address': 'Danube Building - 409 Sheikh Zayed Rd - Al Quoz - Al Quoz 1 - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_dealer', 'heatmap_weight': 1, 'popularity_score': 250.0, 'user_ratings_total': 578, 'popularity_score_category': 'Very High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.2260995, 25.134885699999998]}, 'properties': {'id': 'ChIJ__8_9DRoXz4RlRKV6jrl2GE', 'name': 'Masterkey Luxury Car Rental Dubai', 'phone': '', 'types': ['car_rental', 'point_of_interest', 'establishment'], 'rating': 4.9, 'address': '39 Al Rasaas Rd - Al Quoz - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_rental', 'heatmap_weight': 1, 'popularity_score': 250.0, 'user_ratings_total': 5360, 'popularity_score_category': 'Very High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.3762328, 25.2364394]}, 'properties': {'id': 'ChIJpy3yzZNdXz4RPMYYkGSEyUY', 'name': 'Hertz - Airport Road', 'phone': '', 'types': ['car_rental', 'corporate_office', 'point_of_interest', 'establishment'], 'rating': 3.9, 'address': 'After Emirates Headquarters - Airport Rd - Umm Ramool - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_rental', 'heatmap_weight': 1, 'popularity_score': 250.0, 'user_ratings_total': 584, 'popularity_score_category': 'Very High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.24574, 25.1292141]}, 'properties': {'id': 'ChIJcU1mFMdpXz4RsvHEgZkWBMw', 'name': 'Legend World Rent a Car - Car Rental Dubai - Al Quoz', 'phone': '', 'types': ['car_rental', 'finance', 'point_of_interest', 'establishment'], 'rating': 4, 'address': 'Al Quoz - Al Quoz Industrial Area 2 - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_rental', 'heatmap_weight': 1, 'popularity_score': 250.0, 'user_ratings_total': 611, 'popularity_score_category': 'Very High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.1952911, 25.116203199999998]}, 'properties': {'id': 'ChIJuU0o_7xrXz4RYDtGGLXHW8A', 'name': 'Rotana Star Rent A Car', 'phone': '', 'types': ['car_rental', 'point_of_interest', 'establishment'], 'rating': 4.4, 'address': 'Saratoga Building - Al Barsha - Al Barsha 1 - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_rental', 'heatmap_weight': 1, 'popularity_score': 250.0, 'user_ratings_total': 1651, 'popularity_score_category': 'Very High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.2143344, 25.122674]}, 'properties': {'id': 'ChIJBxc5XtVrXz4RJXoBQ_wu3to', 'name': 'Thrifty Car Rental - Al Quoz Dubai', 'phone': '', 'types': ['car_rental', 'point_of_interest', 'establishment'], 'rating': 3.8, 'address': '23rd St - Al Quoz - Al Quoz Industrial Area 3 - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_rental', 'heatmap_weight': 1, 'popularity_score': 250.0, 'user_ratings_total': 358, 'popularity_score_category': 'Very High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.2372982, 25.1610561]}, 'properties': {'id': 'ChIJfR1LroVpXz4RuhShGvJr6h8', 'name': 'Renty - Rent Luxury Car in Dubai', 'phone': '', 'types': ['car_rental', 'point_of_interest', 'establishment'], 'rating': 4.9, 'address': 'Warehouse 4 - 5th Street - Al Quoz - Al Quoz 3 - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_rental', 'heatmap_weight': 1, 'popularity_score': 250.0, 'user_ratings_total': 2173, 'popularity_score_category': 'Very High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.1512843, 25.0776832]}, 'properties': {'id': 'ChIJbZt4V6ZsXz4RfaHZ5LcGmYw', 'name': 'Afamia Car Rentals', 'phone': '', 'types': ['car_rental', 'point_of_interest', 'establishment'], 'rating': 4.8, 'address': 'Office 1805, JBC - 2 Cluster V - أبراج بحيرات الجميرا - دبي - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_rental', 'heatmap_weight': 1, 'popularity_score': 250.0, 'user_ratings_total': 1104, 'popularity_score_category': 'Very High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.2099208, 25.127855699999998]}, 'properties': {'id': 'ChIJv3m6ZU4TXz4RkhN4VLY_Kiw', 'name': 'Sixt Rent a Car Dubai', 'phone': '', 'types': ['car_rental', 'point_of_interest', 'establishment'], 'rating': 3.5, 'address': 'Sheikh Zayed Rd - Al Quoz - Al Quoz Industrial Area 3 - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_rental', 'heatmap_weight': 1, 'popularity_score': 250.0, 'user_ratings_total': 601, 'popularity_score_category': 'Very High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.2166104, 25.119968399999998]}, 'properties': {'id': 'ChIJ9Qt4J_9rXz4RYpsHbDYWcHE', 'name': 'eZhire Car Rental Al Quoz - Rent a Car Dubai', 'phone': '', 'types': ['car_rental', 'point_of_interest', 'establishment'], 'rating': 2.5, 'address': 'Warehouse S 3 - 23rd St - Al Quoz - Al Quoz Industrial Area 3 - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_rental', 'heatmap_weight': 1, 'popularity_score': 250.0, 'user_ratings_total': 271, 'popularity_score_category': 'Very High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.3723056, 25.1237982]}, 'properties': {'id': 'ChIJ-7V8DktlXz4Rc7hRvid-eS8', 'name': 'AL Emad Car Rental العماد لتأجير السيارات - DSO', 'phone': '', 'types': ['car_rental', 'point_of_interest', 'establishment'], 'rating': 4.5, 'address': 'Dubai Silicon Oasis, Zarooni Building - AL Emad Car Rental, Shop#2 - واحة دبي للسيليكون - دبي - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_rental', 'heatmap_weight': 1, 'popularity_score': 250.0, 'user_ratings_total': 956, 'popularity_score_category': 'Very High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.229177299999996, 25.1558317]}, 'properties': {'id': 'ChIJux01-4hpXz4R0cJiMkF9ZWQ', 'name': 'Nissan Sheikh Zayed Road Dubai - Showroom - Arabian Automobiles LLC', 'phone': '', 'types': ['car_dealer', 'auto_parts_store', 'car_repair', 'store', 'point_of_interest', 'establishment'], 'rating': 4.2, 'address': 'Between 2nd & 3rd Interchange Onpassive Metro Station - Sheikh Zayed Rd - Al Quoz - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_dealer', 'heatmap_weight': 1, 'popularity_score': 200.0, 'user_ratings_total': 1997, 'popularity_score_category': 'High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.2435854, 25.1727304]}, 'properties': {'id': 'ChIJqyNY2etpXz4R4O8T8H9YWPI', 'name': 'Mazda Showroom - Dubai Sheikh Zayed Rd- Galadari Automobiles', 'phone': '', 'types': ['car_dealer', 'point_of_interest', 'store', 'establishment'], 'rating': 4.4, 'address': 'Sheikh Zayed Rd - near Oasis Centre - Al Quoz - Al Quoz 1 - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_dealer', 'heatmap_weight': 1, 'popularity_score': 200.0, 'user_ratings_total': 979, 'popularity_score_category': 'High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.21543500000001, 25.127622600000002]}, 'properties': {'id': 'ChIJh_AsjXZrXz4RtA4qrymXQ9A', 'name': 'Superior Car Rental', 'phone': '', 'types': ['car_rental', 'point_of_interest', 'establishment'], 'rating': 4.7, 'address': 'Warehouse 89 17A St - Al Quoz - Al Quoz Industrial Area 3 - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_rental', 'heatmap_weight': 1, 'popularity_score': 200.0, 'user_ratings_total': 3316, 'popularity_score_category': 'High'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.3364188, 25.263960599999997]}, 'properties': {'id': 'ChIJH01VzmFdXz4RcJJZvnTuLTg', 'name': 'Geely Dubai - AGMC', 'phone': '', 'types': ['car_dealer', 'store', 'point_of_interest', 'establishment'], 'rating': 4.5, 'address': 'E11 - Al Khabaisi - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_dealer', 'heatmap_weight': 1, 'popularity_score': 125.0, 'user_ratings_total': 1180, 'popularity_score_category': 'Low'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.357910999999994, 25.2242537]}, 'properties': {'id': 'ChIJzTDnr3hdXz4RJSZoLn9tjPg', 'name': 'Al-Futtaim Automall - Dubai Festival City', 'phone': '', 'types': ['car_dealer', 'store', 'point_of_interest', 'establishment'], 'rating': 3.6, 'address': 'Next to ACE - Gateway Ave - Dubai Festival City - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_dealer', 'heatmap_weight': 1, 'popularity_score': 125.0, 'user_ratings_total': 2045, 'popularity_score_category': 'Low'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.332865, 25.259617799999997]}, 'properties': {'id': 'ChIJhZ-aO9xcXz4RA0G2HJQqpIw', 'name': 'Nissan Showroom - Arabian Automobiles - Deira', 'phone': '', 'types': ['car_dealer', 'store', 'point_of_interest', 'establishment'], 'rating': 4.2, 'address': 'Nissan Showroom - Al Ittihad Rd - Al Khabaisi - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_dealer', 'heatmap_weight': 1, 'popularity_score': 125.0, 'user_ratings_total': 2068, 'popularity_score_category': 'Low'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.352886999999996, 25.2479721]}, 'properties': {'id': 'ChIJO1UV9wVdXz4R08bcbkkvago', 'name': 'AVIS Rent A Car - Terminal 1 - Departure (CAR RETURN)', 'phone': '', 'types': ['car_rental', 'point_of_interest', 'establishment'], 'rating': 3.6, 'address': '69W2+7HV - 67 Airport Rd - Al Garhoud - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_rental', 'heatmap_weight': 1, 'popularity_score': 125.0, 'user_ratings_total': 623, 'popularity_score_category': 'Low'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.352881599999996, 25.2478492]}, 'properties': {'id': 'ChIJ70cd_wVdXz4RkSHm54BN2DY', 'name': 'Hertz - Dubai Airport Terminal 1', 'phone': '', 'types': ['car_rental', 'point_of_interest', 'establishment'], 'rating': 4, 'address': 'Dubai International Airport، Terminal 1 - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_rental', 'heatmap_weight': 1, 'popularity_score': 125.0, 'user_ratings_total': 1121, 'popularity_score_category': 'Low'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.358269, 25.2450625]}, 'properties': {'id': 'ChIJ-YclOqddXz4R_VcdLXnja1w', 'name': 'Hertz - Dubai Airport Terminal 3', 'phone': '', 'types': ['car_rental', 'point_of_interest', 'establishment'], 'rating': 4.3, 'address': 'Terminal 3 Arrivals Parking Area - دبي - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_rental', 'heatmap_weight': 1, 'popularity_score': 125.0, 'user_ratings_total': 1728, 'popularity_score_category': 'Low'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.3520693, 25.2480965]}, 'properties': {'id': 'ChIJ3SvGAQZdXz4R9ZexhFNZyyE', 'name': 'Dollar Car Rental - Dubai Airport Terminal 1', 'phone': '', 'types': ['car_rental', 'point_of_interest', 'establishment'], 'rating': 4, 'address': 'Dubai International Airport Terminal 1 - دبي - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_rental', 'heatmap_weight': 1, 'popularity_score': 125.0, 'user_ratings_total': 1195, 'popularity_score_category': 'Low'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.3429627, 25.1825703]}, 'properties': {'id': 'ChIJNw_-vrBnXz4R83YY1hT2xio', 'name': 'Shift Car Rental - Ras Al Khor (Al Aweer)', 'phone': '', 'types': ['car_rental', 'point_of_interest', 'establishment'], 'rating': 4.5, 'address': 'Nissan service center, 5th street, Near Aladdin R/A, Ras A Khor 1 - Ras Al Khor Industrial Area - Ras Al Khor Industrial Area 1 - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_rental', 'heatmap_weight': 1, 'popularity_score': 125.0, 'user_ratings_total': 400, 'popularity_score_category': 'Low'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.352845699999996, 25.2477436]}, 'properties': {'id': 'ChIJ7xlgUg9dXz4R6-16Cb_9ugs', 'name': 'Budget Car Rental Return Dubai Airport T1', 'phone': '', 'types': ['car_rental', 'point_of_interest', 'establishment'], 'rating': 3.3, 'address': 'Airport Rd - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_rental', 'heatmap_weight': 1, 'popularity_score': 125.0, 'user_ratings_total': 157, 'popularity_score_category': 'Low'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.360246700000005, 25.2441189]}, 'properties': {'id': 'ChIJ6U2YraBdXz4RAuJf8KDONsQ', 'name': 'Thrifty Car Rental - DXB Airport Terminal 3', 'phone': '', 'types': ['car_rental', 'point_of_interest', 'establishment'], 'rating': 3.8, 'address': 'Dubai Arrivals, Terminal 3 - Dubai International Airport - دبي - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_rental', 'heatmap_weight': 1, 'popularity_score': 100.0, 'user_ratings_total': 708, 'popularity_score_category': 'Low'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.352858000000005, 25.247863199999998]}, 'properties': {'id': 'ChIJXz_mwAVdXz4RDM-rwaVrwMY', 'name': 'Thrifty Car Rental - DXB Airport Terminal 1', 'phone': '', 'types': ['car_rental', 'point_of_interest', 'establishment'], 'rating': 3.9, 'address': 'Airport terminal 1 departure area - Airport Rd - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_rental', 'heatmap_weight': 1, 'popularity_score': 100.0, 'user_ratings_total': 475, 'popularity_score_category': 'Low'}}, {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [55.339802399999996, 25.254931300000003]}, 'properties': {'id': 'ChIJGWZw8WZdXz4RuYstPxg8Ono', 'name': 'GOLDEN KEY RENT CAR LLC\u200f', 'phone': '', 'types': ['car_rental', 'point_of_interest', 'establishment'], 'rating': 4.7, 'address': 'Shop-5 , Dubai International - Cargo Village - Airport Rd - Dubai - United Arab Emirates', 'priceLevel': '', 'primaryType': 'car_rental', 'heatmap_weight': 1, 'popularity_score': 100.0, 'user_ratings_total': 1717, 'popularity_score_category': 'Low'}}
        ],
        'properties': ['primaryType', 'phone', 'id', 'address', 'priceLevel', 'rating', 'heatmap_weight', 'user_ratings_total', 'types', 'popularity_score_category', 'name', 'popularity_score']
    }


@pytest.fixture
def req_save_layer():
    return {
   "message":"Request from frontend",
   "request_info":{

   },
   "request_body":{
      "prdcer_layer_name":"UAE-DUB-CAE",
      "prdcer_lyr_id":"le2014eaa-2330-4765-93b6-1800edd4979f",
      "bknd_dataset_id":"55.2708_25.2048_30000.0_CAFE_token=",
      "points_color":"#007BFF",
      "layer_legend":"UAE-DUB-CAE",
      "layer_description":"",
      "city_name":"Dubai",
      "user_id":"qnVMpp2NbpZArKuJuPL0r9luGP13"
   }
}

@pytest.fixture
def req_save_layer_duplicate():
    return {
   "message":"Request from frontend",
   "request_info":{

   },
   "request_body":{
      "prdcer_layer_name":"UAE-DUB-CAFE",
      "prdcer_lyr_id":"le2014eaa-2330-4765-93b6-1800edd4979f",
      "bknd_dataset_id":"55.2708_25.2048_30000.0_CAFE_token=",
      "points_color":"#007BFF",
      "layer_legend":"UAE-DUB-CAFE",
      "layer_description":"",
      "city_name":"Dubai",
      "user_id":"qnVMpp2NbpZArKuJuPL0r9luGP13"
   }
}

@pytest.fixture
def req_create_user_profile():
    return {
      "message": "string",
      "request_info": {},
      "request_body": {
        "user_id": "",
        "account_type": "admin",
        "admin_id": "string",
        "show_price_on_purchase": False,
        "email": "string",
        "password": "string",
        "username": "string"
      }
}


@pytest.fixture
def user_profile_data():
    return {'admin_id': None, 'prdcer': {'prdcer_ctlgs': {}, 'draft_ctlgs': {}, 'prdcer_dataset': {'dataset_plan': 'plan_cafe_Saudi Arabia_Jeddah', 'plan_CAFE_United Arab Emirates_Dubai': 'plan_CAFE_United Arab Emirates_Dubai', '_Saudi Arabia_Jeddah': 'plan__Saudi Arabia_Jeddah'}, 'prdcer_lyrs': {'le2014eaa-2330-4765-93b6-1800edd4979f': {'city_name': 'Dubai', 'points_color': '#007BFF', 'layer_legend': 'UAE-DUB-CAFE', 'bknd_dataset_id': '55.2708_25.2048_30000.0_CAFE_token=', 'prdcer_layer_name': 'UAE-DUB-CAFE', 'layer_description': '', 'prdcer_lyr_id': 'le2014eaa-2330-4765-93b6-1800edd4979f'}, 'l3c7ff6ea-1c06-42ba-8355-bebf2d32bd1f': {'city_name': 'Jeddah', 'points_color': '#28A745', 'layer_legend': 'full-SA-JED-atm', 'bknd_dataset_id': '39.2271_21.514_3750.0_atm_token=page_token=plan_atm_Saudi Arabia_Jeddah@#$30', 'prdcer_layer_name': 'full-SA-JED-atm', 'layer_description': '', 'prdcer_lyr_id': 'l3c7ff6ea-1c06-42ba-8355-bebf2d32bd1f'}, 'l2d66b0a6-a202-4167-9d1f-b87c0b206d23': {'city_name': 'Jeddah', 'points_color': '#28A745', 'layer_legend': 'SA-JED-gas station', 'bknd_dataset_id': '39.1728_21.5433_30000.0_gas_station_token=', 'prdcer_layer_name': 'SA-JED-gas station', 'layer_description': '', 'prdcer_lyr_id': 'l2d66b0a6-a202-4167-9d1f-b87c0b206d23'}, 'l11428532-878c-4ba2-8fac-18241925d9e9': {'city_name': 'Jeddah', 'points_color': '#007BFF', 'layer_legend': 'SA-JED-embassy', 'bknd_dataset_id': '39.1728_21.5433_30000.0_embassy_token=', 'prdcer_layer_name': 'SA-JED-embassy', 'layer_description': '', 'prdcer_lyr_id': 'l11428532-878c-4ba2-8fac-18241925d9e9'}, 'la43624ae-ef97-4a77-96da-00d92ae5bbaf': {'city_name': 'Jeddah', 'points_color': '#007BFF', 'layer_legend': 'SA-JED-car wash', 'bknd_dataset_id': '39.1728_21.5433_30000.0_car_wash_token=', 'prdcer_layer_name': 'SA-JED-car wash', 'layer_description': '', 'prdcer_lyr_id': 'la43624ae-ef97-4a77-96da-00d92ae5bbaf'}, 'l2bd1d3e1-9646-435d-80ce-0077e81a5352': {'city_name': 'Jeddah', 'points_color': '#28A745', 'layer_legend': 'SA-JED-city hall', 'bknd_dataset_id': '39.1728_21.5433_30000.0_city_hall_token=', 'prdcer_layer_name': 'hall', 'layer_description': '', 'prdcer_lyr_id': 'l2bd1d3e1-9646-435d-80ce-0077e81a5352'}, 'l98330cb1-1b9e-4d1b-a714-be71453a0f88': {'city_name': 'Jeddah', 'points_color': '#FFC107', 'layer_legend': 'SA-JED-fire station', 'bknd_dataset_id': '39.1728_21.5433_30000.0_fire_station_token=', 'prdcer_layer_name': 'SA-JED-fire station', 'layer_description': '', 'prdcer_lyr_id': 'l98330cb1-1b9e-4d1b-a714-be71453a0f88'}, 'lab264e36-92e4-4cce-bbaf-4aa04f7a9d70': {'city_name': 'Jeddah', 'points_color': '#007BFF', 'layer_legend': 'full-SA-JED-cafe', 'bknd_dataset_id': '39.2271_21.514_3750.0_cafe_token=page_token=plan_cafe_Saudi Arabia_Jeddah@#$30', 'prdcer_layer_name': 'full-SA-JED-cafe', 'layer_description': '', 'prdcer_lyr_id': 'lab264e36-92e4-4cce-bbaf-4aa04f7a9d70'}, 'le53c5078-aca9-47e7-8c29-aca3f3aad8fc': {'city_name': 'Jeddah', 'points_color': '#343A40', 'layer_legend': 'SA-JED-bank', 'bknd_dataset_id': '39.1728_21.5433_30000.0_bank_token=', 'prdcer_layer_name': 'SA-JED-bank', 'layer_description': '', 'prdcer_lyr_id': 'le53c5078-aca9-47e7-8c29-aca3f3aad8fc'}}}, 'account_type': 'admin', 'user_id': 'qnVMpp2NbpZArKuJuPL0r9luGP13', 'email': 'omar.trkzi.dev@gmail.com', 'settings': {'show_price_on_purchase': True}, 'username': 'Omar', 'prdcer_lyrs': {'l08b1b66b-c76c-45a1-8c1d-1b5941f99ead': {'progress': 49900}, 'l1b958355-c2da-4640-8ebb-cf71a51facaf': {'progress': 13}}}

@pytest.fixture
def firebase_sign_in():
    return {'kind': 'identitytoolkit#VerifyPasswordResponse', 'localId': 'sUEGmzrKaOW3hBcaOKM73HJLTRa2', 'email': 's.t.1@yopmail.com', 'displayName': 'username', 'idToken': 'eyJhbGciOiJSUzI1NiIsImtpZCI6ImEwODA2N2Q4M2YwY2Y5YzcxNjQyNjUwYzUyMWQ0ZWZhNWI2YTNlMDkiLCJ0eXAiOiJKV1QifQ.eyJuYW1lIjoic2hlaHJhbXRhaGlyIiwiaXNzIjoiaHR0cHM6Ly9zZWN1cmV0b2tlbi5nb29nbGUuY29tL2Rldi1zLWxvY2F0b3IiLCJhdWQiOiJkZXYtcy1sb2NhdG9yIiwiYXV0aF90aW1lIjoxNzQxOTAyNzg3LCJ1c2VyX2lkIjoic1VFR216ckthT1czaEJjYU9LTTczSEpMVFJhMiIsInN1YiI6InNVRUdtenJLYU9XM2hCY2FPS003M0hKTFRSYTIiLCJpYXQiOjE3NDE5MDI3ODcsImV4cCI6MTc0MTkwNjM4NywiZW1haWwiOiJzaGVocmFtLnRhaGlyMTBAeW9wbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6ZmFsc2UsImZpcmViYXNlIjp7ImlkZW50aXRpZXMiOnsiZW1haWwiOlsic2hlaHJhbS50YWhpcjEwQHlvcG1haWwuY29tIl19LCJzaWduX2luX3Byb3ZpZGVyIjoicGFzc3dvcmQifX0.J4KV9yCv4FZGu5nd0qxsKlu3hj0lc_r8fqWezdjtJrJdo0hM-NVfqcX0CsWHOgG8YsZ6USrWA7gqk8iaoLY8IlJLiGW6L_1ArhyIXQJS5KTO7f41vcrePNrQQJJb-9wUEXV63uleSzi1a0jf9yPkMg_kU4kkl_qx4-zk3oW88wOQC7xLZlnXPIfRuWHR6AtFuovvbS_VPrzaiPZ_TxQZ_YecMOl_pK8FXeBrkXD862VU5mHdlNo7j3r3sS-NH73ImU07tMcnHJeaKKfe-iB7_75GgzQ1d1s61017O-8Zd2kQIX135Mdl1pwiVaYa85GpsekDkkbYUphd11ObEou_rg', 'registered': True, 'refreshToken': 'AMf-vBxIVNWONX9vwEOOZ3kvpUlY3map6qLHEX1HG6O9F1OFBl5gdza5eOH3Gm81kSJ530XDtizjm0jLhDFDAIQw782EdmzD5KklJcq8PzAYAwKZt9g5M77x9LzHwed6eTySHuQKKoM4DSFjgToLdfyd0zIUB6sPs3Wv-6nEx_6fb4tJms5ySZYXwrC4RpKYGgeFy7_dG2FoNUnzkIiaGHK6wTV8YGuheHdEXS9tnnW1JOFFEq2atSc', 'expiresIn': '3600'}

@pytest.fixture
def stripe_customer_full_data():
    return {'id': 'cus_RwBlXmU3YsxBAr', 'object': 'customer', 'address': None, 'balance': 0, 'created': 1741901602, 'currency': None, 'default_source': None, 'delinquent': False, 'description': None, 'discount': None, 'email': 's.t6@yopmail.com', 'invoice_prefix': '6C49DABD', 'invoice_settings':  {
      "custom_fields": None,
      "default_payment_method": None,
      "footer": None,
      "rendering_options": None
        },
        'livemode': False,
        'metadata': {
          "user_id": "QxLtKyvwLJaoj8LHo0pOMPo4oew2"
        },
        'name': 'username', 'next_invoice_sequence': 1, 'phone': None, 'preferred_locales': [], 'shipping': None, 'tax_exempt': 'none', 'test_clock': None, 'user_id': 'QxLtKyvwLJaoj8LHo0pOMPo4oew2'}

@pytest.fixture
def req_load_user_profile():
    return {
            "message": "Request from frontend",
            "request_info": {},
            "request_body": {
                "user_id": "123" 
            } }

@pytest.fixture
def req_load_user_profile_duplicate():
    return {
            "message": "Request from frontend",
            "request_info": {},
            "request_body": {
            } }

@pytest.fixture
def res_catlog_collection():
    return {
  "message": "Request received.",
  "request_id": "req-1f6db35d-83fa-4c52-bafd-da5448ce5706",
  "data": [
    {
      "id": "2",
      "name": "Saudi Arabia - Real Estate Transactions",
      "description": "Database of real-estate transactions in Saudi Arabia",
      "thumbnail_url": "https://catalog-assets.s3.ap-northeast-1.amazonaws.com/real_estate_ksa.png",
      "catalog_link": "https://example.com/catalog2.jpg",
      "records_number": 20,
      "can_access": 1
    },
    {
      "id": "55",
      "name": "Saudi Arabia - gas stations poi data",
      "description": "Database of all Saudi Arabia gas stations Points of Interests",
      "thumbnail_url": "https://catalog-assets.s3.ap-northeast-1.amazonaws.com/SAUgasStations.PNG",
      "catalog_link": "https://catalog-assets.s3.ap-northeast-1.amazonaws.com/SAUgasStations.PNG",
      "records_number": 8517,
      "can_access": 0
    }]}

@pytest.fixture
def res_country_city():
    return {
        "United Arab Emirates": [
            {
                "name": "Dubai",
                "lat": 25.2048,
                "lng": 55.2708,
                "bounding_box": [25.1053471, 25.4253471, 55.1324914, 55.4524914],
                "borders": {
                    "northeast": {"lat": 25.3960, "lng": 55.5643},
                    "southwest": {"lat": 24.7921, "lng": 54.8911},
                },
            },
            {
                "name": "Abu Dhabi",
                "lat": 24.4539,
                "lng": 54.3773,
                "bounding_box": [24.2810331, 24.6018540, 54.2971553, 54.7659108],
                "borders": {
                    "northeast": {"lat": 24.5649, "lng": 54.5485},
                    "southwest": {"lat": 24.3294, "lng": 54.2783},
                },
            },
            {
                "name": "Sharjah",
                "lat": 25.3573,
                "lng": 55.4033,
                "bounding_box": [24.7572612, 25.6989797, 53.9777051, 56.6024458],
                "borders": {
                    "northeast": {"lat": 25.4283, "lng": 55.5843},
                    "southwest": {"lat": 25.2865, "lng": 55.2723},
                },
            },
        ],
        "Saudi Arabia": [
            {
                "name": "Riyadh",
                "lat": 24.7136,
                "lng": 46.6753,
                "bounding_box": [19.2083336, 27.7020999, 41.6811300, 48.2582000],
                "borders": {
                    "northeast": {"lat": 24.9182, "lng": 46.8482},
                    "southwest": {"lat": 24.5634, "lng": 46.5023},
                },
            },
            {
                "name": "Jeddah",
                "lat": 21.5433,
                "lng": 39.1728,
                "bounding_box": [21.3904432, 21.7104432, 39.0142363, 39.3342363],
                "borders": {
                    "northeast": {"lat": 21.7432, "lng": 39.2745},
                    "southwest": {"lat": 21.3234, "lng": 39.0728},
                },
            },
            {
                "name": "Mecca",
                "lat": 21.4225,
                "lng": 39.8262,
                "bounding_box": [21.1198192, 21.8480401, 39.5058552, 40.4756100],
                "borders": {
                    "northeast": {"lat": 21.5432, "lng": 39.9283},
                    "southwest": {"lat": 21.3218, "lng": 39.7241},
                },
            },
        ]    }     

@pytest.fixture
def res_layer_matchings_dataset_matching():
    return {'cc': {'records_count': 9191919, 'prdcer_lyrs': ['', '22', '223']}, '39.1728_21.5433_30000.0_book_store_token=': {'records_count': 9191919, 'prdcer_lyrs': ['la823e937-d202-4bdf-a7ed-58b8cfe745f0']}, 'anas': {'records_count': 9191919, 'prdcer_lyrs': ['22']}, '55.2708_25.2048_15000.0_car_rental_token=page_token=plan_car_rental_United Arab Emirates_Dubai@#$1': {'records_count': 9191919, 'prdcer_lyrs': ['l84083b87-bb75-42a0-874f-04e7a8419748']}, 'ayoub': {'records_count': 9191919, 'prdcer_lyrs': ['']}, 'plan_cultural_center_Saudi Arabia_Riyadh': {'records_count': 9191919, 'prdcer_lyrs': ['l4b3fc413-ea4f-46af-9d35-0a563f70a977']}, '54.1552_24.571_15000.0_library_token=page_token=plan_library_United Arab Emirates_Abu Dhabi@#$7': {'records_count': 9191919, 'prdcer_lyrs': ['lce334905-96fd-4ecc-9d7a-3a072f3edd20']}, 'c': {'records_count': 9191919, 'prdcer_lyrs': ['', '22']}, '39.1728_21.5433_30000.0_embassy_token=': {'records_count': 9191919, 'prdcer_lyrs': ['l11428532-878c-4ba2-8fac-18241925d9e9']}, '55.4592_25.328_3750.0_bakery_OR_cafe_OR_coffee_shop_token=page_token=plan_bakery_OR_cafe_OR_coffee_shop_United Arab Emirates_Sharjah@#$30': {'records_count': 9191919, 'prdcer_lyrs': ['lb2d10474-71b4-4d62-8e6f-096acd453161']}, 'plan_car_repair_United Arab Emirates_Sharjah': {'records_count': 9191919, 'prdcer_lyrs': ['ldd075e3d-2c91-414b-afd5-86bab3ac2bc8', 'l3e7c0772-c113-4515-9311-b1d5178a3bf1']}, '55.2708_25.2048_30000.0_art_gallery_token=': {'records_count': 9191919, 'prdcer_lyrs': ['la2cb0445-61b4-4040-b578-cd507bc4f656']}, '39.1728_21.5433_30000.0_car_dealer_OR_car_wash_OR_car_repair_token=': {'records_count': 9191919, 'prdcer_lyrs': ['l2b09d99f-bdfa-4087-8ac2-e273f6f292ab']}, '46.6753_24.7136_30000.0_car_dealer_OR_accounting_token=': {'records_count': 9191919, 'prdcer_lyrs': ['l34c3c481-511c-4234-b408-79d3ede4d536']}, '39.1728_21.5433_30000.0_american_restaurant_token=': {'records_count': 9191919, 'prdcer_lyrs': ['l3fe428f4-c754-4575-9632-0f1e14181261']}, '39.2271_21.514_3750.0_cafe_token=page_token=plan_cafe_Saudi Arabia_Jeddah@#$30': {'records_count': 9191919, 'prdcer_lyrs': ['lab264e36-92e4-4cce-bbaf-4aa04f7a9d70']}, 'plan_preschool_Canada_Toronto': {'records_count': 9191919, 'prdcer_lyrs': ['le6b9f426-34ef-4929-abf7-e92d0d9b05b4']}, '22': {'records_count': 9191919, 'prdcer_lyrs': []}, '39.2271_21.514_3750.0_atm_token=page_token=plan_atm_Saudi Arabia_Jeddah@#$30': {'records_count': 9191919, 'prdcer_lyrs': ['l3c7ff6ea-1c06-42ba-8355-bebf2d32bd1f']}, '39.1728_21.5433_30000.0_library_token=': {'records_count': 9191919, 'prdcer_lyrs': ['l9552f6df-623e-4569-ad3f-36fd715f3b3d', 'l987216fd-d700-4e4b-a79c-bd4cbe1589ee']}, '39.1728_21.5433_30000.0_atm_token=': {'records_count': 9191919, 'prdcer_lyrs': ['l4053fa59-fa63-421e-98d7-8bfe9c2d9f01', 'lce8f5487-b3b7-40d7-8cd2-9f16ad3bf051', 'l350ca9f6-904e-4145-9b2c-20f40ce30b11', 'l967b7ad5-e76c-45cf-846c-d59c6aea0cf7', 'l1b5d0306-9140-4186-873a-8fddeabcc7f1', 'l85e3ad71-2718-4231-b227-aa05fca85f1a', 'lf1114c8e-16d4-441c-ab57-885054f494a4', 'l469ff89b-b8d3-473d-9ce8-7ee2ea858d44', 'ldc826348-61a6-43c4-9187-7590f5034882', 'l93cb85a5-e171-4272-b3c7-bb62aa9897fe', 'lde01b8db-ae4d-4258-a1f3-456623348247', 'l7e2045b1-d2dc-4361-81a8-23478a772997', 'lf0ea37d8-79f4-42d8-9c02-5655055ef3f2', 'la469584e-6f72-44f8-83d5-a01826f28b3c', 'lfb5cc056-2ede-4754-afb0-691324338263', 'lc5ebb92b-0aa9-42ed-ad2b-49718289862a', 'l650ecc4a-986c-4961-9204-da88c24da37f', 'lc27ea09e-3f41-49d9-b5da-0ce6e2e6336a', 'l411db94f-56bb-48c5-b2a1-262a9b049525', 'l8a76cc81-5592-4f7c-953e-7d56e3cf3f31', 'lad862438-447d-4f77-91c2-9643770efa44', 'la407d1e1-c5a1-4a82-b44e-0b3fbe4c6cb8', 'l8d7b184a-f785-4b8e-a34d-114d3196a5ff', 'l3ad11826-2b8e-4439-a0a1-def4fa4ca3b7']}, '39.1728_21.5433_30000.0_car_rental_token=': {'records_count': 9191919, 'prdcer_lyrs': ['l4b4ad771-7f2e-4836-b8c5-21dff62bd3b6', 'lf252f584-d50b-449e-b094-33ae1337f17a', 'l08060bf6-67d2-4a61-a4fa-389c75b0e13a', 'lee44fad7-316b-4848-8be1-276cfbdcdd20']}, '39.1728_21.5433_30000.0_city_hall_token=': {'records_count': 9191919, 'prdcer_lyrs': ['l2bd1d3e1-9646-435d-80ce-0077e81a5352']}, 'census_jeddah_Population Area Intelligence': {'records_count': 9191919, 'prdcer_lyrs': ['lebc56f2d-afc7-4af1-8b59-c772d77ddf58']}, 'plan_car_rental_Saudi Arabia_Riyadh': {'records_count': 9191919, 'prdcer_lyrs': ['la08845cb-5f4d-470d-b18f-ef7ce01de7ac']}, '55.4033_25.3573_30000.0_car_dealer_token=': {'records_count': 9191919, 'prdcer_lyrs': ['l6305c153-f1b0-43d7-82a9-04f60a666101']}, 'plan_school_Canada_Toronto': {'records_count': 9191919, 'prdcer_lyrs': ['le7f77543-95c5-4db2-851a-0ddf280dff13']}, 'plan_casino_Saudi Arabia_Riyadh': {'records_count': 9191919, 'prdcer_lyrs': ['l0beb0ad2-50fd-4076-9e03-408b5e20ba39']}, '54.4328_24.4246_3750.0_gas_station_token=page_token=plan_gas_station_United Arab Emirates_Abu Dhabi@#$30': {'records_count': 9191919, 'prdcer_lyrs': ['lf80f7b92-bddf-4cd3-847e-3ad2a4fb7cef']}, '-79.3134_43.6824_3750.0_ice_cream_shop_token=page_token=plan_ice_cream_shop_Canada_Toronto@#$29': {'records_count': 9191919, 'prdcer_lyrs': ['ladd741a3-e951-472d-a218-d74454617274']}, 'plan_bed_and_breakfast_Saudi Arabia_Riyadh': {'records_count': 9191919, 'prdcer_lyrs': ['lf4099916-5dbf-40d8-aa3c-8d5ed33a77d0']}, '55.2708_25.2048_30000.0_CAFE_token=': {'records_count': 9191919, 'prdcer_lyrs': ['le2014eaa-2330-4765-93b6-1800edd4979f']}, 'plan_preschool_Saudi Arabia_Mecca': {'records_count': 9191919, 'prdcer_lyrs': ['l981cb3e3-8b8a-4ccc-8a72-715a33a04e2d']}, '39.2271_21.514_3750.0_car_rental_token=page_token=plan_car_rental_Saudi Arabia_Jeddah@#$30': {'records_count': 9191919, 'prdcer_lyrs': ['l3bc914bc-e252-4371-af37-09fa92d9b2b7']}, 'cec': {'records_count': 9191919, 'prdcer_lyrs': ['2423']}, '39.1728_21.5433_30000.0_fire_station_token=': {'records_count': 9191919, 'prdcer_lyrs': ['l98330cb1-1b9e-4d1b-a714-be71453a0f88']}, '46.6753_24.7136_30000.0_bank_token=': {'records_count': 9191919, 'prdcer_lyrs': ['l5409369d-a3a8-4038-b603-d1a3631e5124', 'l2ca5a9cd-a08a-4cb5-b0e5-e9673d0a9bae', 'l199f1848-11a9-4ab4-b66b-585322e31435', 'l00f64675-263c-41cc-be93-07f5db3cc7bb', 'l465cc321-de36-4f63-ac8a-a3d01f2d1976', 'l1d77aec5-0c4c-4733-9297-bb6bc4f2a41a', 'l81efac1d-a032-4447-867e-61c5d5c8811d', 'l67449e8d-9751-469e-98c2-60488fc14b2f', 'l377b10c6-dc20-4882-bac0-af52ebe0a32a', 'lcd97d4a8-8253-4ffa-9627-21cd70f4e58a', 'l708faf2e-3ccf-43d7-a91d-e7de7c9624a4', 'l4e19e8e0-e95a-4493-a709-8f2f60547894', 'l292bf97e-aee3-4105-9656-39ef6e96c390', 'l33f9b77f-e6f0-417f-9649-c00379ddfdb1', 'lbe1f09d4-4e03-4edd-afe0-382aced23e25', 'lf5836a56-d237-40c2-b1e2-53e503166487', 'lced25a5a-131b-4c40-9784-5bcd40b38eb8', 'lf1c77396-ee9c-4db5-a871-54a8be592280']}, '55.4943_25.2046_7500.0_car_rental_token=page_token=plan_car_rental_United Arab Emirates_Dubai@#$19': {'records_count': 9191919, 'prdcer_lyrs': ['l09e0e464-6e76-46b6-a5a2-1f993e56d254']}, '46.6753_24.7136_30000.0_museum_OR_performing_arts_theater_OR_school_token=': {'records_count': 9191919, 'prdcer_lyrs': ['l580f9fc3-ff17-4c0b-838c-ea7095932685']}, 'string': 
{'records_count': 9191919, 'prdcer_lyrs': ['']}, '39.1728_21.5433_30000.0_car_dealer_token=': {'records_count': 9191919, 'prdcer_lyrs': ['l64d958fe-9dfb-45a1-ab54-77aff4ebd1a2', 'le210fbbd-5706-49e2-8aaf-7a7f91ccfd94', 'l6c8d8e62-a905-4034-bff4-f3309e05c2c4', 'l0b4a517e-977c-4d2c-bc8d-873de9464c5a', 'lc9d02623-6e02-496b-a4c1-06ea0a3d201a', 'l259ee6e1-e339-430e-a62a-97cc64b8f97d']}, '39.8804_21.3932_3750.0_cafe_token=page_token=plan_cafe_Saudi Arabia_Mecca@#$30': {'records_count': 9191919, 'prdcer_lyrs': ['l8f0d9037-8217-4636-a33f-69bd6249ac50']}, '39.1728_21.5433_30000_university_token=': {'records_count': 9191919, 'prdcer_lyrs': ['lc86df6aa-bda4-4277-b206-580db49b2e26']}, '39.8262_21.4225_30000_atm_token=': {'records_count': 9191919, 'prdcer_lyrs': ['lb2ca5029-c448-448a-99bc-c54d20572e55']}, 'plan_amusement_center_Saudi Arabia_Riyadh': {'records_count': 9191919, 'prdcer_lyrs': ['l1fa8ac00-a88b-4236-b0f7-f50ec670e06b']}, '55.2708_25.2048_30000.0_car_dealer_token=': {'records_count': 9191919, 'prdcer_lyrs': ['lf03f8c40-7562-484a-a7ec-84439ff98271', 'l226f6b52-b628-4608-91e3-c322baf3f5c2']}, '-79.3832_43.6532_3750.0_car_dealer_token=page_token=plan_car_dealer_Canada_Toronto@#$27': {'records_count': 9191919, 'prdcer_lyrs': ['l011a92dc-f1db-4321-8063-b2c11c93b4d3']}, 'plan_city_hall_Saudi Arabia_Jeddah': {'records_count': 9191919, 'prdcer_lyrs': ['l2463d519-1473-4209-8996-d77048fbfe39']}, 'a': 
{'records_count': 9191919, 'prdcer_lyrs': ['22']}, '55.3266_25.1755_3750.0_car_rental_token=page_token=plan_car_rental_United Arab Emirates_Dubai@#$30': {'records_count': 9191919, 'prdcer_lyrs': ['l1e1a6b6b-6bc6-4bbc-8719-ee56582b35fd']}, '39.1728_21.5433_30000.0_car_repair_token=': {'records_count': 9191919, 'prdcer_lyrs': ['l76dd110a-fd68-47ea-91d6-537ab86acbd7']}, 'plan_banquet_hall_Saudi Arabia_Riyadh': {'records_count': 9191919, 'prdcer_lyrs': ['l20d95009-08a3-467d-8690-0b7fed196168']}, '39.2271_21.514_3750.0_atm_OR_bank_token=page_token=plan_atm_OR_bank_Saudi Arabia_Jeddah@#$30': {'records_count': 9191919, 'prdcer_lyrs': ['l37907abe-3124-4d34-8651-40f35f6f8d41']}, 'afsdcc': {'records_count': 9191919, 'prdcer_lyrs': ['']}, 'plan_library_Saudi Arabia_Mecca': {'records_count': 9191919, 'prdcer_lyrs': ['l1361fade-5dce-486c-b819-c442a7b2523e']}, 'plan_car_dealer_Saudi Arabia_Jeddah': {'records_count': 9191919, 'prdcer_lyrs': ['l466acd9e-419b-42d2-922c-01a09b51b119', 'l0aa6fc34-5eed-4b95-99cc-66bd35eed576']}, '54.4328_24.4246_3750.0_car_rental_token=page_token=plan_car_rental_United Arab Emirates_Abu Dhabi@#$30': {'records_count': 9191919, 'prdcer_lyrs': ['l2f1ca7f1-a61a-4245-b828-84e354945585']}, 'plan_camping_cabin_Saudi Arabia_Riyadh': {'records_count': 9191919, 'prdcer_lyrs': ['l91e1ea58-e5c6-4d4d-a87b-d0325059485a']}, 'plan_library_Canada_Toronto': {'records_count': 9191919, 'prdcer_lyrs': ['l0c780da9-03b8-4917-be1e-ce8003f667b7']}, '55.2708_25.2048_30000.0_accounting_token=': {'records_count': 9191919, 'prdcer_lyrs': []}, '46.6753_24.7136_30000.0_atm_token=': {'records_count': 9191919, 'prdcer_lyrs': ['l7011e4ab-1b48-4cda-9c55-6349a868536b', 'l352a1711-58a2-441d-afd1-29b8ecd92b2f', 'le9f7521f-b51d-46fc-9c20-ae04b51ce12d', 'l4dd46fcf-4e51-428b-aea9-02d34d5b34cb', 'ld3cd369b-8420-4469-b780-c446a61a6bf1', 'lb578d63c-512e-4852-81a8-0760062c2000', 'l7c9ee560-f6ab-4308-8373-eb99c89f9161', 'ld244d296-7f23-4511-a6ff-8a0a04154a59', 'l2d011c13-19d4-439f-998b-b2c363bba56f', 'l9486fde8-3eb0-4405-9263-eed719adb38d', 'l25b9407d-8dab-4ab8-8bea-649804eae93d', 'l96873589-f998-4bb5-bda9-08c5a3fcac07', 'lc23e6127-8a2d-4f94-af2c-d467807dd662', 'l7c75b0fc-ab05-4d02-8ad6-b25757bf2943', 'l1887b1f6-c0cf-4444-ab7e-b70b79b40b53', 'l59e8649f-8bbd-4bfb-99f7-9328e28578e2', 'l4b68b13d-cf06-4201-b58f-5832108cbc99', 'l86817bd7-cb68-483c-922f-db0bbe8c1f59', 'lbd8fc89f-497b-41ba-b1f6-de8217a83642']}, 'plan_car_repair_Saudi Arabia_Riyadh': {'records_count': 9191919, 'prdcer_lyrs': ['l60c63860-3e71-4ef5-b18d-9ab73fa00b07']}, '54.3773_24.4539_30000.0_art_gallery_token=': {'records_count': 9191919, 'prdcer_lyrs': ['ldb1ffcd0-c4af-4923-8139-1391448c5145']}, '54.3773_24.4539_7500.0_car_dealer_OR_car_rental_token=page_token=plan_car_dealer_OR_car_rental_United Arab Emirates_Abu Dhabi@#$8': {'records_count': 9191919, 'prdcer_lyrs': ['l7e57075a-f353-48c9-a1d3-d3d164390bc9']}, 'plan_courthouse_Saudi Arabia_Jeddah': {'records_count': 9191919, 'prdcer_lyrs': ['l5a8c29c1-b9bc-4f41-bfb5-3015ba22a610']}, 'plan_car_dealer_United Arab Emirates_Sharjah': {'records_count': 9191919, 'prdcer_lyrs': ['l24cd8bc0-0a36-4563-a6ed-c42644e8f934', 'lb69c709b-da3f-4b20-a811-bb7f9c5bf7ef']}, '39.1728_21.5433_30000.0_car_wash_token=': {'records_count': 9191919, 'prdcer_lyrs': ['ldf0533ed-9722-40c8-b175-23b2f02c9f04', 'la43624ae-ef97-4a77-96da-00d92ae5bbaf']}, '39.1728_21.5433_30000.0_gas_station_token=': {'records_count': 9191919, 'prdcer_lyrs': ['l2d66b0a6-a202-4167-9d1f-b87c0b206d23']}, 'plan_cafe_Saudi Arabia_Jeddah': {'records_count': 9191919, 'prdcer_lyrs': ['lf883f239-8c38-4980-9100-668d4da16286']}, '55.3266_25.1755_3750.0_car_dealer_token=page_token=plan_car_dealer_United Arab Emirates_Dubai@#$30': {'records_count': 9191919, 'prdcer_lyrs': ['l786c150b-5a19-410c-ada1-3e80c08d6f1b']}, 'plan_car_dealer_Saudi Arabia_Riyadh': {'records_count': 9191919, 'prdcer_lyrs': ['l68d9f916-f560-4aeb-a89b-806cd5612727']}, 'plan_car_repair_Saudi Arabia_Jeddah': {'records_count': 9191919, 'prdcer_lyrs': ['ld56e382a-6bbf-4fbe-a3ec-3722655c9f71', 'l2ee138a9-a387-43ba-b906-94f6673e035a']}, '1': {'records_count': 9191919, 'prdcer_lyrs': ['']}, '39.1728_21.5433_30000.0__token=_text_search=tekken_': {'records_count': 9191919, 'prdcer_lyrs': ['l2118eba9-18b4-4634-8eff-3d9ddc7f08c5']}, '39.1728_21.5433_30000.0_bank_token=': {'records_count': 9191919, 'prdcer_lyrs': ['l782f163d-1468-4017-9f27-175f2fa8cc4e', 'lf3fb1ede-1b22-4a71-b4a8-a7d9a48f0d34', 'l26629314-e048-4441-8204-00fa542e8a0c', 'la064bee0-ec6f-45f3-94d3-9c7203f5622e', 'l4f545dbe-7d89-406a-82a0-9624e078da76', 'lcbc3085c-5110-4a33-8540-9184de7bc48f', 'lfb04f601-a336-46dc-8a07-f7087d037a91', 'lfd0605b2-1466-49dc-be36-13184b668ea1', 'l7b6ff839-f799-4080-bd43-5a19760143cb', 'l2e86e48a-b64f-4e23-8792-b7ee57282524', 'ld919ffb1-291c-4d77-b2fe-f4e9dc9077b3', 'lfe14f35a-ec53-470b-908a-5be16d0ee2fc', 'l86c2c8ff-79f5-4ca3-9226-e5c07b77ce2f', 'le53c5078-aca9-47e7-8c29-aca3f3aad8fc']}, '54.4328_24.4246_3750.0_car_dealer_token=page_token=plan_car_dealer_United Arab Emirates_Abu Dhabi@#$30': {'records_count': 9191919, 'prdcer_lyrs': ['l7de79d0d-b645-4ea7-8086-903c4baffb46']}, '39.8262_21.4225_30000_city_hall_token=': {'records_count': 9191919, 'prdcer_lyrs': ['l15f2f069-3e4f-40e0-abd1-45256dacacec']}, '39.1728_21.5433_30000_car_dealer_token=': {'records_count': 9191919, 'prdcer_lyrs': ['l8cfe0eb1-943d-45e6-b9f7-c37695e4e524']}, '39.2271_21.514_3750.0_car_dealer_token=page_token=plan_car_dealer_Saudi Arabia_Jeddah@#$30': {'records_count': 9191919, 'prdcer_lyrs': ['lba87e2f8-7156-4adc-874c-802dd7f65d66', 'le69b56d7-3123-4777-aa4f-16bbef54dce5']}, '55.3266_25.1755_3750.0_car_repair_token=page_token=plan_car_repair_United Arab Emirates_Dubai@#$30': {'records_count': 9191919, 'prdcer_lyrs': ['l677c6a8c-dd2d-460a-8a96-3ee1038cf631']}, 'b': {'records_count': 9191919, 'prdcer_lyrs': ['', '2343423', '22']}, 'plan_car_rental_Saudi Arabia_Jeddah': {'records_count': 9191919, 'prdcer_lyrs': ['l3c846cfd-9eb1-49ce-873d-c3385860e466']}}


@pytest.fixture
def res_layer_matchings_user_matching():
    return {'le2014eaa-2330-4765-93b6-1800edd4979f': 'qnVMpp2NbpZArKuJuPL0r9luGP13', 'l7e2045b1-d2dc-4361-81a8-23478a772997': 'gPwQrwJJE4XVDDRiwFJIbKCgRPC3', 'l59e8649f-8bbd-4bfb-99f7-9328e28578e2': 'gPwQrwJJE4XVDDRiwFJIbKCgRPC3'}


@pytest.fixture
def producer_catalog_data():
    return {
        "prdcer_ctlg_name": "string",
        "prdcer_ctlg_id": "string",
        "subscription_price": "string",
        "ctlg_description": "string",
        "total_records": 0,
        "lyrs": [
            {
                "layer_id": "string",
                "points_color": "string"
            }
        ],
        "thumbnail_url": "https://storage.googleapis.com/bucket_name/path/to/file.jpg",
        "ctlg_owner_user_id": "string",
        "display_elements": {}
    }



@pytest.fixture
def req_save_producer_catlog():
    return {
        "req_data": {  # Raw Python dict instead of JSON string
            "message": "string",
            "request_info": {},
            "request_body": {
                "user_id": "string",
                "prdcer_ctlg_name": "string",
                "subscription_price": "string",
                "ctlg_description": "string",
                "total_records": 0,
                "lyrs": [{"layer_id": "string", "points_color": "string"}],
                "display_elements": {},
                "catalog_layer_options": {},
                "addtional_info": {},
                "image": None
            }
        },
        "image": ("test.png")
    }

@pytest.fixture
def req_cost_calculator():
    return{
       "message": "string",
       "request_info": {
             "additionalProp1": {}
         },
        "request_body": {
                "lat": 0,
                "lng": 0,
                "user_id": "string",
                "prdcer_lyr_id": "",
                "city_name": "montreal",
                "country_name": "canada",
                "boolean_query": "business_for_rent",
                "action": "",
                "page_token": "",
                "search_type": "default",
                "text_search": "",
                "zoom_level": 0,
                "radius": 30000
                    }
                }

@pytest.fixture
def req_llm_query():
    return {
  "message": "string",
  "request_info": {
    "additionalProp1": {}
  },
  "request_body": {
    "query": "cafes in Dubai"
  }
}

@pytest.fixture
def res_llm_query():
    return {
        "content": '```json\n{\n  "query": "cafes in Dubai",\n  "is_valid": "Valid",\n  "reason": "",\n  "endpoint": "/fastapi/fetch_dataset",\n  "suggestions": [],\n  "body": {\n    "lat": null,\n    "lng": null,\n    "user_id": "",\n    "prdcer_lyr_id": "",\n    "city_name": "Dubai",\n    "country_name": "United Arab Emirates",\n    "boolean_query": "CAFE",\n    "action": "",\n    "page_token": "",\n    "search_type": "default",\n    "text_search": "",\n    "zoom_level": 0,\n    "radius": 30000.0\n  },\n  "cost": ""\n}\n```'
    }
import pytest
from typing import Optional, List

@pytest.fixture
def req_GradientColorBasedOnZone():
    return {
        "message": "request from front end",
        "request_info" : {},
        "request_body":{
        "color_grid_choice": ["#FF0000", "#00FF00", "#0000FF"],
        "change_lyr_id": "le2014eaa-2330-4765-93b6-1800edd4979f",
        "change_lyr_name": "Layer Name",
        "change_lyr_orginal_color": "#CCCCCC",  
        "change_lyr_new_color": "#FFFFFF",      
        "based_on_lyr_id": "le2014eaa-2330-4765-93b6-1800edd4979f",
        "based_on_lyr_name": "Base Layer",
        "coverage_value": 300.0,                
        "coverage_property": "Radius",          
        "color_based_on": "rating",             
        "list_names": []  }                     
    }



@pytest.fixture
def req_check_street_view():
    return {
        "message": "Request from frontend",
        "request_info": {},
        "request_body": {
            "lat": 37.7749,    
            "lng": -122.4194   
        }
    }

@pytest.fixture
def invalid_prompt_validation_response():
    return {
        "message": "Request received.",
        "request_id": "req-b8e738f8-6388-466c-8f79-2643c02a2c71",
        "data": {
            "is_valid": False,
            "reason": "Request is incomplete. It needs to specify the layers, operation (recolor/filter), and parameters for the operation.",
            "suggestions": [
                "Specify which layer you want to recolor or filter.",
                "Specify the type of operation you want to perform (e.g., recolor, filter).",
                "Provide the parameters for the operation, such as distance, color, or names to filter by."
            ],
            "endpoint": None
        }
    }

@pytest.fixture
def req_auth_user_data():
    return {
        'localId': 'Ox67BapY2ddZ2K3DSCVVgqARGna2',
        'email': 'sharif@gmail.com',
        'displayName': 'string',
        'emailVerified': True,
        'disabled': False,
        'lastLoginAt': '1744814953948',
        'createdAt': '1740336918877',
        'lastRefreshAt': '2025-04-16T14:49:13.948Z',
        'providerUserInfo': [
            {
                'providerId': 'password',
                'displayName': 'string',
                'federatedId': 'sharif@gmail.com',
                'email': 'sharif@gmail.com',
                'rawId': 'sharif@gmail.com'
            }
        ]
    }

@pytest.fixture
def firebase_api_request_refresh_token():
    return {'access_token': 'eyJhbGciOiJSUzI1NiIsImtpZCI6Ijg1NzA4MWNhOWNiYjM3YzIzNDk4ZGQzOTQzYmYzNzFhMDU4ODNkMjgiLCJ0eXAiOiJKV1QifQ.eyJuYW1lIjoic3RyaW5nIiwiaXNzIjoiaHR0cHM6Ly9zZWN1cmV0b2tlbi5nb29nbGUuY29tL2Rldi1zLWxvY2F0b3IiLCJhdWQiOiJkZXYtcy1sb2NhdG9yIiwiYXV0aF90aW1lIjoxNzQ0ODkzNTg2LCJ1c2VyX2lkIjoiT3g2N0JhcFkyZGRaMkszRFNDVlZncUFSR25hMiIsInN1YiI6Ik94NjdCYXBZMmRkWjJLM0RTQ1ZWZ3FBUkduYTIiLCJpYXQiOjE3NDQ4OTM2NjIsImV4cCI6MTc0NDg5NzI2MiwiZW1haWwiOiJzaGFyaWZkZXJoZW1AZ21haWwuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsImZpcmViYXNlIjp7ImlkZW50aXRpZXMiOnsiZW1haWwiOlsic2hhcmlmZGVyaGVtQGdtYWlsLmNvbSJdfSwic2lnbl9pbl9wcm92aWRlciI6InBhc3N3b3JkIn19.XWKD0SKhhGBW2nZ1a85S1B_icXc3ujWd8SPe3QS9XS9sFAjAMCaLpVoV5TKx1t38SD9uo033cfTlpmCRHOFk_ESVGCF5ap2SKLumn42viTUcFuG5cUXDbh_7upROJTl0ICFKHHN_0I12qph4pbeKdTVOW0HRt59eoxKGTw4Ph3YN642FkOgm5WCClstiFv5A7Hk_Q11LFY9L1Qnyev_3-xQAKlD2QJt7QfZFfuHayE3gy08FC5RsEQMoUoOeQIsxQNZbs-n4Rr9teI-q5COoq7Yd_dpXE_jsggj45TZAcl-2FLPhbmCo9j9D1O1l10t_miiz-vEUsKzINxrAtc7_CA', 'expires_in': '3600', 'token_type': 'Bearer', 'refresh_token': 'AMf-vBzoT0GbO4IENbpBjyUugPWV7jsOMYrvPi7gutTXCsp7KDzTmpApkUXnmnlgzw42Lbb3jQcPDhFhlKD_sKiRRNHQgyM3hYoMkg1KrpegEeKMupLaz6pEuE3IB80CQfZwfUdIYnFaA4RxhIoREoAYiiWMIANQDNEjeHZQn6JO5m8mGHVErdwXzDWxlBxBUMVn3hRyGmK-alChKCaP-KvaXxEUVfa5Lgu_A77JkE89-kw0gbgVUkU', 'id_token': 'eyJhbGciOiJSUzI1NiIsImtpZCI6Ijg1NzA4MWNhOWNiYjM3YzIzNDk4ZGQzOTQzYmYzNzFhMDU4ODNkMjgiLCJ0eXAiOiJKV1QifQ.eyJuYW1lIjoic3RyaW5nIiwiaXNzIjoiaHR0cHM6Ly9zZWN1cmV0b2tlbi5nb29nbGUuY29tL2Rldi1zLWxvY2F0b3IiLCJhdWQiOiJkZXYtcy1sb2NhdG9yIiwiYXV0aF90aW1lIjoxNzQ0ODkzNTg2LCJ1c2VyX2lkIjoiT3g2N0JhcFkyZGRaMkszRFNDVlZncUFSR25hMiIsInN1YiI6Ik94NjdCYXBZMmRkWjJLM0RTQ1ZWZ3FBUkduYTIiLCJpYXQiOjE3NDQ4OTM2NjIsImV4cCI6MTc0NDg5NzI2MiwiZW1haWwiOiJzaGFyaWZkZXJoZW1AZ21haWwuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsImZpcmViYXNlIjp7ImlkZW50aXRpZXMiOnsiZW1haWwiOlsic2hhcmlmZGVyaGVtQGdtYWlsLmNvbSJdfSwic2lnbl9pbl9wcm92aWRlciI6InBhc3N3b3JkIn19.XWKD0SKhhGBW2nZ1a85S1B_icXc3ujWd8SPe3QS9XS9sFAjAMCaLpVoV5TKx1t38SD9uo033cfTlpmCRHOFk_ESVGCF5ap2SKLumn42viTUcFuG5cUXDbh_7upROJTl0ICFKHHN_0I12qph4pbeKdTVOW0HRt59eoxKGTw4Ph3YN642FkOgm5WCClstiFv5A7Hk_Q11LFY9L1Qnyev_3-xQAKlD2QJt7QfZFfuHayE3gy08FC5RsEQMoUoOeQIsxQNZbs-n4Rr9teI-q5COoq7Yd_dpXE_jsggj45TZAcl-2FLPhbmCo9j9D1O1l10t_miiz-vEUsKzINxrAtc7_CA', 'user_id': 'Ox67BapY2ddZ2K3DSCVVgqARGna2', 'project_id': '379100953236'}

@pytest.fixture
def req_update_stripe_customer():
    return{
  "message": "string",
  "request_info": {
    "additionalProp1": {}
  },
  "request_body": {
    "user_id": "user_id",
    "phone": "string",
    "address": {
      "city": "string",
      "country": "string",
      "line1": "string",
      "line2": "string",
      "postal_code": "string",
      "state": "string"
    },
    "balance": 0,
    "currency": "string",
    "default_source": "string",
    "delinquent": True,
    "description": "string",
    "discount": "string",
    "name": "string",
    "email": "personofpersons@gmail.com",
    "invoice_prefix": "string",
    "invoice_settings": {
      "additionalProp1": {}
    },
    "metadata": {
      "additionalProp1": {}
    }
  }
}
import pytest

@pytest.fixture
def res_list_stripe_customers():
    return {
        "data": [
            {
                "address": None,
                "balance": 0,
                "created": 1744839861,
                "currency": None,
                "default_source": None,
                "delinquent": False,
                "description": None,
                "discount": None,
                "email": "frontend1@traz.xyz",
                "id": "cus_S8vcPMuIxktXCr",
                "invoice_prefix": "136159B3",
                "invoice_settings": {
                    "custom_fields": None,
                    "default_payment_method": None,
                    "footer": None,
                    "rendering_options": None
                },
                "livemode": False,
                "metadata": {
                    "user_id": "WIhoMP52pkbHgwkDQNB3Y0qWOED3"
                },
                "name": "frontend dev",
                "next_invoice_sequence": 1,
                "object": "customer",
                "phone": None,
                "preferred_locales": [],
                "shipping": None,
                "tax_exempt": "none",
                "test_clock": None
            },
        ]
    }

@pytest.fixture
def req_route_info():
    return {
  "message": "Requesting short distance route",
  "request_info": {},
  "request_body": {
    "source": {
      "lat": 40.730610,
      "lng": -73.935242
    },
    "destination": {
      "lat": 40.732610,
      "lng": -73.937242
    }
  }
 }


@pytest.fixture
def res_route_info():
    leg_info_mock = MagicMock()
    leg_info_mock.start_location = {
        "latLng": {"latitude": 40.7304541, "longitude": -73.9350043}
    }
    leg_info_mock.end_location = {
        "latLng": {"latitude": 40.7326421, "longitude": -73.9371842}
    }
    leg_info_mock.distance = 432.0
    leg_info_mock.duration = "109s"
    leg_info_mock.static_duration = "109s"
    leg_info_mock.polyline = "idrwFvlgbMa@c@Y_@IIQUIKQY_BlCW`@e@r@QRuCxCi@f@R`@LXLZ?BBF@F@DAB?BABA@CB"
    leg_info_mock.traffic_conditions = [
        {"start_index": 0, "end_index": 27, "speed": "NORMAL"}
    ]

    route_info_mock = MagicMock()
    route_info_mock.origin = "40.73061,-73.935242"
    route_info_mock.destination = "40.73261,-73.937242"
    route_info_mock.route = [leg_info_mock]

    return route_info_mock

@pytest.fixture
def res_route_info_duplicate():
    route_info_mock = MagicMock()
    route_info_mock.origin = "40.73061,-73.935242"
    route_info_mock.destination = "40.73261,-73.937242"
    route_info_mock.route = []  # Empty list to trigger the exception!
    
    return route_info_mock
    leg_info_mock = MagicMock()
    leg_info_mock.start_location = {
        "latLng": {"latitude": 40.7304541, "longitude": -73.9350043}
    }
    leg_info_mock.end_location = {
        "latLng": {"latitude": 40.7326421, "longitude": -73.9371842}
    }
    leg_info_mock.distance = 432.0
    leg_info_mock.duration = "109s"
    leg_info_mock.static_duration = "109s"
    leg_info_mock.polyline = "idrwFvlgbMa@c@Y_@IIQUIKQY_BlCW`@e@r@QRuCxCi@f@R`@LXLZ?BBF@F@DAB?BABA@CB"
    leg_info_mock.traffic_conditions = [
        {"start_index": 0, "end_index": 27, "speed": "NORMAL"}
    ]

    route_info_mock = MagicMock()
    route_info_mock.origin = "40.73061,-73.935242"
    route_info_mock.destination = "40.73261,-73.937242"
    route_info_mock.route = [leg_info_mock]

    return route_info_mock

@pytest.fixture
def req_gadientcolorBasedOnZone():
    return {
        "message": "request from front end",
        "request_info" : {},
        "request_body":{
            "change_lyr_id": "change_lyr_id",
            "based_on_lyr_id": "base_lyr_id",
            "color_based_on": "rating" # or user_ratings_total
        
        }                     
    }

@pytest.fixture
def res_gradientcolor_based_on_zone():
    return {
        "data": {
            "ResGradientColorBasedOnZone": [
                # Layer 1 (Lowest values)
                {
                    "type": "FeatureCollection",
                    "features": [{
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [12.34, 56.78]},
                        "properties": {"rating": 1.2, "name": "Place A"}
                    }],
                    "properties": ["rating"],
                    "prdcer_layer_name": "Rating 1.0-1.7",
                    "prdcer_lyr_id": "lyr_123:gradient1",
                    "sub_lyr_id": "gradient_segment_1",
                    "bknd_dataset_id": "dataset_123",
                    "points_color": "#FF0000",
                    "layer_legend": "1.0-1.7",
                    "layer_description": "Bottom 14% of ratings",
                    "records_count": 1,
                    "city_name": "TestCity",
                    "is_zone_lyr": "true"
                },
                # Layer 2
                {
                    "type": "FeatureCollection",
                    "features": [{
                        "type": "Feature", 
                        "geometry": {"type": "Point", "coordinates": [12.35, 56.79]},
                        "properties": {"rating": 1.8, "name": "Place B"}
                    }],
                    "properties": ["rating"],
                    "prdcer_layer_name": "Rating 1.7-2.4",
                    "prdcer_lyr_id": "lyr_123:gradient2",
                    "sub_lyr_id": "gradient_segment_2",
                    "points_color": "#FF5500",
                    "layer_legend": "1.7-2.4",
                    "records_count": 1,
                    # ... other required fields ...
                },
                # Layers 3-6 (similar structure with different ranges/colors)
                # ...
                # Layer 7 (Highest values)
                {
                    "type": "FeatureCollection",
                    "features": [{
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [12.40, 56.85]},
                        "properties": {"rating": 4.8, "name": "Place G"}
                    }],
                    "properties": ["rating"],
                    "prdcer_layer_name": "Rating 4.3-5.0",
                    "prdcer_lyr_id": "lyr_123:gradient7", 
                    "sub_lyr_id": "gradient_segment_7",
                    "points_color": "#00FF00",
                    "layer_legend": "4.3-5.0",
                    "records_count": 1,
                    # ... other required fields ...
                }
            ]
        }
    }
