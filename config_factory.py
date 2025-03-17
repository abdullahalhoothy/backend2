import json
import os
from dataclasses import dataclass, fields, is_dataclass
from backend_common.common_config import CommonApiConfig



@dataclass
class ApiConfig(CommonApiConfig):
    backend_base_uri: str = "/fastapi/"
    ggl_base_url: str = "https://places.googleapis.com/v1/places:"
    nearby_search: str = ggl_base_url + "searchNearby"
    search_text: str = ggl_base_url + "searchText"
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
    fetch_dataset_full_data: str = backend_base_uri + "fetch_dataset/full_data"
    fetch_dataset: str = backend_base_uri + "fetch_dataset"
    save_layer: str = backend_base_uri + "save_layer"
    delete_layer: str = backend_base_uri + "delete_layer"
    user_layers: str = backend_base_uri + "user_layers"
    prdcer_lyr_map_data: str = backend_base_uri + "prdcer_lyr_map_data"
    nearest_lyr_map_data: str = backend_base_uri + "nearest_lyr_map_data"
    save_producer_catalog: str = backend_base_uri + "save_producer_catalog"
    delete_producer_catalog: str = backend_base_uri + "delete_producer_catalog"
    user_catalogs: str = backend_base_uri + "user_catalogs"
    fetch_ctlg_lyrs: str = backend_base_uri + "fetch_ctlg_lyrs"
    apply_zone_layers: str = backend_base_uri + "apply_zone_layers"
    cost_calculator: str = backend_base_uri + "cost_calculator"
    check_street_view: str = backend_base_uri + "check_street_view"
    google_fields: str = (
        "places.id,places.types,places.location,places.rating,places.priceLevel,places.userRatingCount,places.displayName,places.primaryType,places.formattedAddress,places.takeout,places.delivery,places.paymentOptions"
    )
    save_draft_catalog: str = backend_base_uri + "save_draft_catalog"
    fetch_gradient_colors :str = backend_base_uri + "fetch_gradient_colors"
    gradient_color_based_on_zone :str = backend_base_uri + "gradient_color_based_on_zone"
    filter_based_on :str = backend_base_uri + "filter_based_on"
    
    gcloud_slocator_bucket_name:str = "s-locator"
    gcloud_images_bucket_path:str = "postgreSQL/dbo_operational/raw_schema_marketplace/catalog_thumbnails"
    gcloud_bucket_credentials_json_path:str = "secrets/weighty-gasket-437422-h6-a9caa84da98d.json"
    process_llm_query:str = backend_base_uri + "process_llm_query"
    openai_api_key:str=""
    gemini_api_key:str=""

    @classmethod
    def get_conf(cls):
        common_conf = CommonApiConfig.get_common_conf()
        conf = cls(**{f.name: getattr(common_conf, f.name) for f in fields(CommonApiConfig)})

        try:
            if os.path.exists("secrets/secrets_gmap.json"):
                with open("secrets/secrets_gmap.json", "r", encoding="utf-8") as config_file:
                    data = json.load(config_file)
                    conf.api_key = data.get("gmaps_api", "")
                    conf.openai_api_key = data.get("openai_api_key", "")
                    conf.gemini_api_key = data.get("gemini_api_key", "")

            return conf
        except Exception as e:
            return conf


CONF = ApiConfig.get_conf()