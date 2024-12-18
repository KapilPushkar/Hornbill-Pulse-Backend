from pydantic import BaseModel, Field
from typing import List
from .coordinates import Coordinates

class LandRequest(BaseModel):
    coordinates: List[Coordinates]
    user_id: str = Field(...)
    land_name: str = Field(...)

class VegetationRequest(BaseModel):
    coordinates: List[List[float]]
    year: int

class LandCreate(LandRequest):
    coordinates: List[Coordinates]
    user_id: str = Field(...)
    land_name: str = Field(...)
    id: str = Field(..., alias="_id")

class LandResponse(LandRequest):
    id: str = Field(..., alias="_id")

    class Config:
        populate_by_name = True 

class LandAnalysisReportRequest(BaseModel):
    userId: str = Field(...)
    coordinates: List[List[float]] = Field(...)
    fcm_token: str = Field(...)
