from typing import Dict, List, TypeVar, Generic, Literal, Any, Optional

from pydantic import BaseModel, Field


class ResCostEstimate(BaseModel):
    cost: float
    api_calls: int


class Geometry(BaseModel):
    type: Literal["Point"]
    coordinates: List[float]


class Feature(BaseModel):
    type: Literal["Feature"]
    properties: dict
    geometry: Geometry


class LyrInfoInCtlgSave(BaseModel):
    layer_id: str
    points_color: str = Field(
        ..., description="Color name for the layer points, e.g., 'red'"
    )


class card_metadata(BaseModel):
    id: str
    name: str
    description: str
    thumbnail_url: str
    catalog_link: str
    records_number: int
    can_access: int


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


class CityData(BaseModel):
    name: str
    lat: float
    lng: float
    type: str = None


class ResFetchDataset(BaseModel):
    type: Literal["FeatureCollection"]
    features: List[Feature]
    bknd_dataset_id: str
    prdcer_lyr_id: str
    records_count: int
    next_page_token: Optional[str] = ""


class UserCatalogInfo(BaseModel):
    prdcer_ctlg_id: str
    prdcer_ctlg_name: str
    ctlg_description: str
    thumbnail_url: str
    subscription_price: str
    total_records: int
    lyrs: List[LyrInfoInCtlgSave] = Field(..., description="list of layer objects.")
    ctlg_owner_user_id: str


T = TypeVar("T")


class ResModel(BaseModel, Generic[T]):
    message: str
    request_id: str
    data: T


ResAllCards = ResModel[List[card_metadata]]

ResUserLayers = ResModel[List[LayerInfo]]

ResCtlgLyrs = ResModel[List[PrdcerLyrMapData]]
ResApplyZoneLayers = ResModel[List[PrdcerLyrMapData]]
ResCreateUserProfile = ResModel[Dict[str, str]]
ResSavePrdcerCtlg = ResModel[str]
ResTypeMapData = ResModel[MapData]

ResCountryCityData = ResModel[Dict[str, List[CityData]]]
ResNearbyCategories = ResModel[Dict[str, List[str]]]
ResPrdcerLyrMapData = ResModel[PrdcerLyrMapData] 
ResOldNearbyCategories = ResModel[List[str]]
ResUserCatalogs = ResModel[List[UserCatalogInfo]]
ResUserLogin = ResModel[Dict[str, Any]]
ResUserProfile = ResModel[Dict[str, Any]]
ResResetPassword = ResModel[Dict[str, Any]]
ResConfirmReset = ResModel[Dict[str, Any]]
ResChangePassword = ResModel[Dict[str, Any]]
