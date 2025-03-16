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


@pytest.fixture
async def get_auth_header(async_client):  # TODO
    login_data = {"username": "testuser", "password": "securepassword"}
    response = await async_client.post("/login", data=login_data)
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json().get("access_token")}"}


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