from fastapi import APIRouter, Depends, HTTPException
from typing import List
from ....models.schemas.land import LandRequest, LandResponse
from ....services.land import LandService

router = APIRouter()

@router.post("", response_model=LandResponse)
async def create_land(
    land_request: LandRequest,
    land_service: LandService = Depends()
):
    return await land_service.create_land(land_request)

@router.put("/{land_id}", response_model=LandResponse)
async def update_land(
    land_id: str, 
    land_data: LandRequest,
    land_service: LandService = Depends()
):
    try:
        updated_land = await land_service.update_land(land_id, land_data)
        if not updated_land:
            raise HTTPException(status_code=404, detail="Land not found")
        return updated_land
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
