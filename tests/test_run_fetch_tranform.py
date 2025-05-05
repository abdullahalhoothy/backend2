import pytest

# def test_create_feature_collection():
#     from scripts.database_transformation import create_feature_collection
#
#     # Input data
#     input_data = [{"price":'3800000', "additional__weblisting_uri___location_lat":'24.903622' ,"additional__weblisting_uri___location_lng":'46.787441',"price":'3800000',"specifications_فيلا_في_السطح":None,"specifications_مؤثثة":None ,"specifications_مدخل_سيارة":"متوفر"}]
#
#     # Expected output
#     expected_output = {
#         "type": "FeatureCollection",
#         "features": [
#             {
#                 "type": "Feature",
#                 "properties": {
#                     "price": "3800000",
#                     "specifications_فيلا_في_السطح": None,
#                     "specifications_مؤثثة": None,
#                     "specifications_مدخل_سيارة": "متوفر"
#                 },
#                 "geometry": {
#                     "type": "Point",
#                     "coordinates": [ 24.903622,46.787441]
#                 }
#             }
#         ]
#     }
#
#     # Call the function
#     result = create_feature_collection(input_data)
#
#     # Assert that the result matches the expected output
#     assert result == expected_output
#
#     # Additional checks
#     assert result["type"] == "FeatureCollection"
#     assert len(result["features"]) == 1
#     assert result["features"][0]["type"] == "Feature"
#     assert result["features"][0]["geometry"]["type"] == "Point"
#
#     # Check if coordinates are floats
#     assert isinstance(result["features"][0]["geometry"]["coordinates"][0], float)
#     assert isinstance(result["features"][0]["geometry"]["coordinates"][1], float)
#
#     # Check specific values
#     assert result["features"][0]["properties"]["price"] == "3800000"
#     assert result["features"][0]["properties"]["specifications_فيلا_في_السطح"] is None
#     assert result["features"][0]["properties"]["specifications_مؤثثة"] is None
#     assert result["features"][0]["properties"]["specifications_مدخل_سيارة"] == "متوفر"