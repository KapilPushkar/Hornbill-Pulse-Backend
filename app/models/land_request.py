from pydantic import BaseModel
from typing import List
from .coordinates import Coordinates

class LandRequest(BaseModel):
    coordinates: List[Coordinates]
    user_id: str
    land_name: str
