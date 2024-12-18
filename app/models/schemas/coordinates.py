from pydantic import BaseModel, Field
from typing import List

class Coordinates(BaseModel):
    lat: float = Field(...)
    long: float = Field(...) 