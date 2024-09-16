import json
import os
from dataclasses import dataclass, fields, is_dataclass


@dataclass
class static_ApiConfig:
    api_key: str = ""
    backend_base_uri: str = "/fastapi/"
    firebase_api_key: str = ""
    firebase_sp_path: str = ""
    firebase_base_url: str = "https://identitytoolkit.googleapis.com/v1/accounts:"
    firebase_refresh_token = f"{firebase_base_url[:-9]}token?key="      ## Change 
    firebase_signInWithPassword = f"{firebase_base_url}signInWithPassword?key="
    firebase_sendOobCode = f"{firebase_base_url}sendOobCode?key="
    firebase_resetPassword = f"{firebase_base_url}resetPassword?key="
    firebase_signInWithCustomToken = f"{firebase_base_url}signInWithCustomToken?key="
    firebase_update = f"{firebase_base_url}update?key="
    ggl_base_url: str = "https://places.googleapis.com/v1/places:"
    nearby_search: str = ggl_base_url + "searchNearby"
    place_details: str = ggl_base_url + "details/json"
    enable_CORS_url: str = "http://localhost:3000"
    catlog_collection: str = backend_base_uri + "catlog_collection"
    layer_collection: str = backend_base_uri + "layer_collection"
    fetch_acknowlg_id: str = backend_base_uri + "fetch_acknowlg_id"
    catlog_data: str = backend_base_uri + "ws_dataset_load/{request_id}"
    http_catlog_data: str = backend_base_uri + "http_catlog_data"
    single_nearby: str = backend_base_uri + "ws/{request_id}"
    http_single_nearby: str = backend_base_uri + "http_single_nearby"
    country_city: str = backend_base_uri + "country_city"
    nearby_categories: str = backend_base_uri + "nearby_categories"
    old_nearby_categories: str = backend_base_uri + "old_nearby_categories"
    fetch_dataset: str = backend_base_uri + "fetch_dataset"
    save_layer: str = backend_base_uri + "save_layer"
    user_layers: str = backend_base_uri + "user_layers"
    prdcer_lyr_map_data: str = backend_base_uri + "prdcer_lyr_map_data"
    save_producer_catalog: str = backend_base_uri + "save_producer_catalog"
    user_catalogs: str = backend_base_uri + "user_catalogs"
    fetch_ctlg_lyrs: str = backend_base_uri + "fetch_ctlg_lyrs"
    apply_zone_layers: str = backend_base_uri + "apply_zone_layers"
    create_user_profile: str = backend_base_uri + "create_user_profile"
    reset_password = backend_base_uri + "reset-password"
    confirm_reset = backend_base_uri + "confirm-reset"
    change_password = backend_base_uri + "change-password"
    login: str = backend_base_uri + "login"
    refresh_token = backend_base_uri + "refresh-token"     ## Change
    user_profile: str = backend_base_uri + "user_profile"
    cost_calculator: str = backend_base_uri + "cost_calculator"
    google_fields: str = (
        "places.id,places.types,places.location,places.rating,places.priceLevel,places.userRatingCount,places.displayName,places.primaryType,places.formattedAddress,places.takeout,places.delivery,places.paymentOptions"
    )
    save_draft_catalog: str = backend_base_uri + "save_draft_catalog"
    fetch_gradient_colors :str = backend_base_uri + "fetch_gradient_colors"
    gradient_color_based_on_zone :str = backend_base_uri + "gradient_color_based_on_zone"
    


@dataclass
class ConfigDict:
    def __init__(self, dictionary):
        for key, value in dictionary.items():
            if isinstance(value, dict):
                setattr(self, key, ConfigDict(value))
            else:
                setattr(self, key, value)


class ConfigFactory:
    @staticmethod
    def load_config(file_path: str, config_class):
        # Load configuration from a JSON file
        with open(file_path, "r") as config_file:
            config_data = json.load(config_file)

        # Recursively convert dictionaries to instances of the config class
        return ConfigFactory._dict_to_object(config_data, config_class)

    @staticmethod
    def _dict_to_object(data, config_class):
        if not is_dataclass(config_class):
            raise TypeError(f"{config_class} is not a dataclass type")

        # Create an instance of the config class
        obj = config_class(**{f.name: None for f in fields(config_class)})

        for key, value in data.items():
            if isinstance(value, dict):
                # Set nested dictionaries as ConfigDict objects for attribute access
                setattr(obj, key, ConfigDict(value))
            else:
                setattr(obj, key, value)

        return obj


# Example usage
# Assuming the JSON configuration file looks something like this:
# {
#     "api_key": "your_api_key",
#     "base_urls": {
#         "google": "https://maps.googleapis.com/maps/api",
#         "bing": "https://dev.virtualearth.net/REST/v1"
#     }
# }
# # Loading configuration
# config = ConfigFactory.load_config(
#     'G:\\My Drive\\Personal\\Work\\offline\\Jupyter\\Git\\s_locator\\common_settings.json', ApiCommonConfig)
# print(config.api_key)  # Output: your_api_key
# print(config.base_urls.google)  # Output: https://maps.googleapis.com/maps/api


def get_conf() -> static_ApiConfig:
    conf = static_ApiConfig()
    try:
        with open("secrets/secrets_gmap.json", "r", encoding="utf-8") as config_file:
            data = json.load(config_file)
            conf.api_key = data.get("gmaps_api", "")

        if os.path.exists("secrets/secrets_firebase.json"):
            with open("secrets/secrets_firebase.json", "r", encoding="utf-8") as config_file:
                data = json.load(config_file)
                conf.firebase_api_key = data.get("firebase_api_key", "")
                conf.firebase_sp_path = data.get("firebase_sp_path", "")

        return conf
    except Exception as e:
        return conf
