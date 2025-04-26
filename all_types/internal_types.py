from typing import Any, List
from pydantic import BaseModel, Field


class LyrInfoInCtlgSave(BaseModel):
    layer_id: str
    points_color: str = Field(
        ..., description="Color name for the layer points, e.g., 'red'"
    )


class PrdcerCtlg(BaseModel):
    prdcer_ctlg_name: str
    subscription_price: str
    ctlg_description: str
    total_records: int
    lyrs: List[LyrInfoInCtlgSave] = Field(..., description="list of layer objects.")
    display_elements: dict[str, Any] = Field(default_factory=dict, description="Flexible field for frontend to store arbitrary key-value pairs")
    catalog_layer_options:  dict[str, Any] = Field(default_factory=dict, description="Flexible field for frontend to store arbitrary key-value pairs")


class UserId(BaseModel):
    user_id: str