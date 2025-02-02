from typing import List, Optional
from fastapi import HTTPException
from shapely.geometry import Polygon
from shapely.ops import transform
from pyproj import Transformer
from ..repositories.land import LandRepository
from ..models.schemas.land import LandRequest, LandResponse, LandCreate
from ..db.mongodb import db
from bson import ObjectId
from datetime import datetime

class LandService:
    def __init__(self):
        self.repository = LandRepository()

    async def create_land(self, land_request: LandRequest) -> LandResponse:
        land_dict = land_request.model_dump()
        land_dict["created_at"] = datetime.utcnow()
        land_dict["modified_at"] = datetime.utcnow()

        coordinates = [(coord[1], coord[0]) for coord in land_request.coordinates]

        polygon = Polygon(coordinates)
        
        transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
        projected_polygon = transform(transformer.transform, polygon)
        
        area_sq_m = projected_polygon.area

        if area_sq_m >= 1e4:
            land_dict["area"] = round(area_sq_m / 1e4, 2)
            land_dict["area_unit"] = "hectares"
        elif area_sq_m >= 4046.86:
            land_dict["area"] = round(area_sq_m / 4046.86, 2)
            land_dict["area_unit"] = "acres"
        else:
            land_dict["area"] = round(area_sq_m, 2)
            land_dict["area_unit"] = "sq/m"

        existing_lands = await self.repository.find_many({"user_id": land_request.user_id})
        existing_names = [land["land_name"] for land in existing_lands]
        original_name = land_request.land_name
        counter = 1
        while land_request.land_name in existing_names:
            land_dict["land_name"] = f"{original_name} {counter}"
            counter += 1

        created_land = await self.repository.create(land_dict)
        if not created_land:
            raise HTTPException(status_code=400, detail="Failed to create land")
        return created_land

    async def update_land(self, land_id: str, land_data: LandRequest) -> Optional[LandResponse]:
        try:
            update_data = land_data.model_dump()
            update_data["modified_at"] = datetime.utcnow()
            
            result = await db.land.update_one(
                {"_id": ObjectId(land_id)},
                {"$set": update_data}
            )
            
            if result.modified_count:
                updated_land = await db.land.find_one({"_id": ObjectId(land_id)})
                if updated_land:
                    updated_land["id"] = str(updated_land.pop("_id"))
                    return LandResponse(**updated_land)
            return None
            
        except Exception as e:
            raise Exception(f"Error updating land: {str(e)}")
        
    async def get_land(self, land_id: str) -> Optional[LandCreate]:
        land = await self.repository.find_one(land_id)
        if not land:
            raise HTTPException(status_code=404, detail="Land not found")
        land["_id"] = str(land["_id"])
        return LandCreate(**land)

    async def get_lands_by_user_id(self, user_id: str) -> List[LandResponse]:
        lands = await self.repository.find_many({"user_id": user_id})
        for land in lands:
            land["_id"] = str(land["_id"])
        return [LandResponse(**land) for land in lands]

    async def delete_land(self, land_id: str) -> bool:
        result = await self.repository.delete(land_id)
        return result
