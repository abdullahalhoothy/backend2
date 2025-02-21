from typing import Dict, List, TypeVar, Generic, Literal, Any, Optional, Union

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResModel(BaseModel, Generic[T]):
    message: str
    request_id: str
    data: T


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


class MapData(BaseModel):
    type: Literal["FeatureCollection"]
    features: List[Feature]
    properties:list[str]


class CityData(BaseModel):
    name: str
    lat: float
    lng: float
    borders: Any
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


class LayerInfo(BaseModel):
    prdcer_layer_name: str
    prdcer_lyr_id: str
    bknd_dataset_id: str
    points_color: str
    layer_legend: str
    layer_description: str
    records_count: int
    city_name: str
    is_zone_lyr: str


class ResLyrMapData(MapData, LayerInfo):
    pass


class TrafficCondition(BaseModel):
    start_index: int
    end_index: int
    speed: Optional[str]


class LegInfo(BaseModel):
    start_location: dict
    end_location: dict
    distance: float
    duration: str
    static_duration: str
    polyline: str
    traffic_conditions: List[TrafficCondition]


class RouteInfo(BaseModel):
    origin: str
    destination: str
    route: List[LegInfo]


class NearestPointRouteResponse(BaseModel):
    target: dict
    routes: List[Union[RouteInfo, dict]]


class ResGradientColorBasedOnZone(ResLyrMapData):
    sub_lyr_id: str  # This is the additional property


class ResAddPaymentMethod(BaseModel):
    payment_method_id: str
    status: str


class PaymentMethod(BaseModel):
    id: str
    type: str
    details: Dict[str, Any]


class ResGetPaymentMethods(BaseModel):
    payment_methods: List[PaymentMethod]

# types for llm agents
class ResGradientColorBasedOnZoneLLM(BaseModel):
    layers: List[ResGradientColorBasedOnZone]
    explanation: str  # This is the additional property

class ValidationResult(BaseModel):
    is_valid: bool
    reason: Optional[str] = None
    suggestions: Optional[List[str]] = None

class ResProcessColorBasedOnLLM(ResGradientColorBasedOnZoneLLM):
    validation_result:ValidationResult


class ResLLMDataset(BaseModel):
    """Extract Location Based Information from the Query"""

    query: str = Field(
        default = "",
        description = "Original query passed by the user."
    )
    queryStatus: Literal["Valid", "Invalid"] = Field(
        default="Valid",
        description="Status of the query that depends on approved categories.It must be either 'Valid' or 'Invalid'"
    )
    message: str = Field(
        default = "",
        description = "Response message for the User after processing the query. It helps user to identify issues in the query"
    )
    requestStatus: Literal["Processed", "NotProcessed"] = Field(
        default="NotProcessed",
        description="Set to processed whenever an LLM encounters the query is processed by the LLM"
    )
    fetch_dataset_request: Optional[ResFetchDataset] = Field(
        default=None,
        description="An object containing detailed request parameters for fetching dataset"
    )
    cost: str = Field(
        default = '',
        description = "The cost value returned by calculate_cost_tool"
    )