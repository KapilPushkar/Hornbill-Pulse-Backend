from pydantic import BaseModel, Field
from typing import List

class LandRequest(BaseModel):
    coordinates: List[List[float]] = Field(...)
    user_id: str = Field(...)
    land_name: str = Field(...)
    area: float = Field(default=0.0)
    area_unit: str = Field(default="sq/m")
    status: str = Field(default="Submitted")
    user_name: str = Field(default="")
    user_email: str = Field(default="")

class LandCreate(LandRequest):
    coordinates: List[List[float]] = Field(...)
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
