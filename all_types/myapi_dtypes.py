from typing import Dict, List, TypeVar, Generic, Optional

from pydantic import BaseModel, Field

from all_types.response_dtypes import LyrInfoInCtlgSave

U = TypeVar("U")


class Coordinate(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None


class ReqUserId(BaseModel):
    user_id: str


class ReqModel(BaseModel, Generic[U]):
    message: str
    request_info: Dict
    request_body: U


class ReqCityCountry(BaseModel):
    city_name: str
    country_name: str


class boxmapProperties(BaseModel):
    name: str
    rating: float
    address: str
    phone: str
    website: str
    business_status: str
    user_ratings_total: int


class ReqSavePrdcerCtlg(ReqUserId):
    prdcer_ctlg_name: str
    subscription_price: str
    ctlg_description: str
    total_records: int
    lyrs: List[LyrInfoInCtlgSave] = Field(..., description="list of layer objects.")
    # thumbnail_url: str
    display_elements: dict
    catalog_layer_options: dict


class ReqDeletePrdcerCtlg(ReqUserId):
    prdcer_ctlg_id: str


class ZoneLayerInfo(BaseModel):
    lyr_id: str
    property_key: str


class ReqCatalogId(BaseModel):
    catalogue_dataset_id: str


class ReqPrdcerLyrMapData(ReqUserId):
    prdcer_lyr_id: Optional[str] = ""


class ReqSavePrdcerLyer(ReqPrdcerLyrMapData):
    prdcer_layer_name: str
    bknd_dataset_id: str
    points_color: str
    layer_legend: str
    layer_description: str
    city_name: str


class ReqDeletePrdcerLayer(BaseModel):
    user_id: str
    prdcer_lyr_id: str


class ReqFetchDataset(ReqCityCountry, ReqPrdcerLyrMapData, Coordinate):
    boolean_query: Optional[str] = ""
    action: Optional[str] = ""
    page_token: Optional[str] = ""
    search_type: Optional[str] = "default"
    text_search: Optional[str] = ""
    zoom_level: Optional[int] = 0
    radius: Optional[float] = 30000.0
    _bounding_box: Optional[list[float]] = []
    _included_types: Optional[list[str]] = []
    _excluded_types: Optional[list[str]] = []


# class ReqCustomData(ReqCityCountry):
#     boolean_query: Optional[str] = ""
#     page_token: Optional[str] = ""
#     included_types: list[str] = []
#     excluded_types: list[str] = []
#     zoom_level: Optional[int] = 0


# class ReqLocation(Coordinate):
#     radius: float
#     bounding_box: list[float]
#     page_token: Optional[str] = ""
#     text_search: Optional[str] = ""
#     boolean_query: Optional[str] = ""
#     zoom_level: Optional[int] = 0


class ReqFetchCtlgLyrs(BaseModel):
    prdcer_ctlg_id: str
    as_layers: bool
    user_id: str


class ReqCostEstimate(ReqCityCountry):
    included_categories: List[str]
    excluded_categories: List[str]


class ReqStreeViewCheck(Coordinate):
    pass


class ReqGeodata(Coordinate):
    bounding_box: list[float]


class ReqNearestRoute(ReqPrdcerLyrMapData):
    points: List[Coordinate]


class ReqGradientColorBasedOnZone(BaseModel):
    color_grid_choice: list[str]
    change_lyr_id: str
    change_lyr_name: str
    change_lyr_orginal_color: Optional[str] = "#CCCCCC"
    change_lyr_new_color: Optional[str] = "#FFFFFF"
    based_on_lyr_id: str
    based_on_lyr_name: str
    coverage_value: float  # [10min , 20min or 300 m or 500m]
    coverage_property: str  # [Drive_time or Radius]
    color_based_on: str  # ["rating" or "user_ratings_total"]
    list_names: Optional[List[str]] = []
    

class ReqPrompt(BaseModel):
    user_id: str
    prompt: str
