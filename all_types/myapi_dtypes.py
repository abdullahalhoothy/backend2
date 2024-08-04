from typing import Dict, List, TypeVar, Generic, Literal, Any, Optional

from pydantic import BaseModel, Field


# class ResDefault(BaseModel):
#     message: str
#     request_id: str


class card_metadata(BaseModel):
    id: str
    name: str
    description: str
    thumbnail_url: str
    catalog_link: str
    records_number: int
    can_access: int


class Geometry(BaseModel):
    type: Literal["Point"]
    coordinates: List[float]


class boxmapProperties(BaseModel):
    name: str
    rating: float
    address: str
    phone: str
    website: str
    business_status: str
    user_ratings_total: int


class Feature(BaseModel):
    type: Literal["Feature"]
    properties: dict
    geometry: Geometry


class CityData(BaseModel):
    name: str
    lat: float
    lng: float
    type: str = None


class DataCreateLyr(BaseModel):
    type: Literal["FeatureCollection"]
    features: List[Feature]
    bknd_dataset_id: str
    prdcer_lyr_id: str
    records_count: int
    next_page_token: Optional[str] = ""


class ReqSavePrdcerLyer(BaseModel):
    prdcer_layer_name: str
    prdcer_lyr_id: str
    bknd_dataset_id: str
    points_color: str
    layer_legend: str
    layer_description: str
    user_id: str


class LayerInfo(BaseModel):
    prdcer_lyr_id: str
    prdcer_layer_name: str
    points_color: str
    layer_legend: str
    layer_description: str
    records_count: int
    is_zone_lyr: str


class MapData(BaseModel):
    type: Literal["FeatureCollection"]
    features: List[Feature]


class PrdcerLyrMapData(MapData):
    prdcer_layer_name: str
    prdcer_lyr_id: str
    bknd_dataset_id: str
    points_color: str
    layer_legend: str
    layer_description: str
    records_count: int
    is_zone_lyr: str


class LyrInfoInCtlgSave(BaseModel):
    layer_id: str
    points_color: str = Field(
        ..., description="Color name for the layer points, e.g., 'red'"
    )


class ReqSavePrdcerCtlg(BaseModel):
    prdcer_ctlg_name: str
    subscription_price: str
    ctlg_description: str
    total_records: int
    lyrs: List[LyrInfoInCtlgSave] = Field(..., description="list of layer objects.")
    user_id: str
    thumbnail_url: str


class UserCatalogInfo(BaseModel):
    prdcer_ctlg_id: str
    prdcer_ctlg_name: str
    ctlg_description: str
    thumbnail_url: str
    subscription_price: str
    total_records: int
    lyrs: List[LyrInfoInCtlgSave] = Field(..., description="list of layer objects.")
    ctlg_owner_user_id: str


class ZoneLayerInfo(BaseModel):
    lyr_id: str
    property_key: str


# Request models
class ReqLocation(BaseModel):
    lat: float
    lng: float
    radius: int
    excludedTypes:list[str]
    includedTypes:list[str]
    page_token: Optional[str] = ""
    text_search: Optional[str] = ""


class ReqCatalogId(BaseModel):
    catalogue_dataset_id: str


class ReqUserId(BaseModel):
    user_id: str


class ReqPrdcerLyrMapData(BaseModel):
    prdcer_lyr_id: str
    user_id: str


class ReqCreateLyr(BaseModel):
    dataset_country: str
    dataset_city: str
    excludedTypes:list[str]
    includedTypes:list[str]
    action: Optional[str] = ""
    page_token: Optional[str] = ""
    search_type: Optional[str] = "default"
    text_search: Optional[str] = ""
    user_id: str


class ReqApplyZoneLayers(BaseModel):
    user_id: str
    lyrs: List[str]
    lyrs_as_zone: List[Dict[str, str]]


class ReqCreateUserProfile(BaseModel):
    username: str
    email: str
    password: str


class ReqFetchCtlgLyrs(BaseModel):
    prdcer_ctlg_id: str
    as_layers: bool
    user_id: str


class ReqUserLogin(BaseModel):
    email: str
    password: str


class ReqUserProfile(BaseModel):
    user_id: str


class ReqResetPassword(BaseModel):
    email: str


class ReqConfirmReset(BaseModel):
    oob_code: str
    new_password: str


class ReqChangePassword(BaseModel):
    user_id:str
    email:str
    password:str
    new_password: str


T = TypeVar("T")
U = TypeVar("U")


class ResponseModel(BaseModel, Generic[T]):
    message: str
    request_id: str
    data: T


ResAllCards = ResponseModel[List[card_metadata]]
ResUserLayers = ResponseModel[List[LayerInfo]]
ResCtlgLyrs = ResponseModel[List[PrdcerLyrMapData]]
ResApplyZoneLayers = ResponseModel[List[PrdcerLyrMapData]]
ResCreateUserProfile = ResponseModel[Dict[str, str]]
ResAcknowlg = ResponseModel[str]
ResSavePrdcerCtlg = ResponseModel[str]
ResTypeMapData = ResponseModel[MapData]
ResCountryCityData = ResponseModel[Dict[str, List[CityData]]]
ResNearbyCategories = ResponseModel[Dict[str, List[str]]]
ResPrdcerLyrMapData = ResponseModel[PrdcerLyrMapData]
ResCreateLyr = ResponseModel[DataCreateLyr]
ResOldNearbyCategories = ResponseModel[List[str]]
ResUserCatalogs = ResponseModel[List[UserCatalogInfo]]
ResUserLogin = ResponseModel[Dict[str, Any]]
ResUserProfile = ResponseModel[Dict[str, Any]]
ResResetPassword = ResponseModel[Dict[str, Any]]
ResConfirmReset = ResponseModel[Dict[str, Any]]
ResChangePassword = ResponseModel[Dict[str, Any]]


class ReqModel(BaseModel, Generic[U]):
    message: str
    request_info: Dict
    request_body: U
