from typing import List
from pydantic import BaseModel, Field

class Coordinate(BaseModel):
    lat: float
    long: float

class CoordinatesList(BaseModel):
    coordinates: List[Coordinate]