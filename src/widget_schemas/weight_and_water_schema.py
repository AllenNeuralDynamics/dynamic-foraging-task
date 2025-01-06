from pydantic import Field, BaseModel


class WeightAndWater(BaseModel):
    """
    Schema for weight and water widget
    """

    base_weight_g: float = Field(title="Base weight of mouse in grams")
    target_weight_g: float = Field(title="Target weight of mouse in grams")
    target_ratio: float = Field(default=.85, title="Target ratio of mouse")
    total_water_mL: float = Field(title="Total water in ml")
    supplemental_mL: float = Field(title="Supplemental water in ml")
    post_weight_g: float = Field(title="Post weight of mouse in grams")
