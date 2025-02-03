from fastapi import APIRouter, Depends, HTTPException
from typing import List
from ....models.schemas.land import LandRequest, LandResponse
from ....services.land import LandService
from ....worker import add_task
from ....services.land_vegetation import generate_land_analysis_report
from ....utils.serializers import serialize_to_response

router = APIRouter()

@router.post("", response_model=LandResponse)
async def create_land(
    land_request: LandRequest,
    land_service: LandService = Depends()
):
    land = await land_service.create_land(land_request)
    add_task(lambda: generate_land_analysis_report(land['user_id'], str(land['_id']), land['coordinates']))
    
    return serialize_to_response(land)

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

@router.get("/user/{user_id}", response_model=List[LandResponse])
async def get_lands_by_user_id(
    user_id: str,
    land_service: LandService = Depends()
):
    try:
        lands = await land_service.get_lands_by_user_id(user_id)
        return lands
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{land_id}", response_model=dict)
async def delete_land(
    land_id: str,
    land_service: LandService = Depends()
):
    try:
        deleted = await land_service.delete_land(land_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Land not found")
        return {"message": "Land deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
