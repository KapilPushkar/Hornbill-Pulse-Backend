from pydantic import BaseModel
from typing import Dict, Optional
from datetime import datetime

class VegetationStats(BaseModel):
    land_id: str
    yearly_data: Dict
    report_path: Optional[str] = None
    created_at: datetime = datetime.utcnow() 