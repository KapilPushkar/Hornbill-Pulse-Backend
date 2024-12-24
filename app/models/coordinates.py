from typing import List
from pydantic import BaseModel, Field
class CoordinatesList(BaseModel):
    coordinates: List[List[float]]