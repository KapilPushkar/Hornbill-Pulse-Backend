from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Optional
from ....models.schemas.land import LandRequest, LandResponse, LandCreate, VegetationRequest, LandAnalysisReportRequest
from ....services.land import LandService
from ....services.land_vegetation import get_monthly_vegetation_stats, generate_land_analysis_report
router = APIRouter()

@router.post("/lands", response_model=LandResponse)
async def create_land(
    land_request: LandRequest,
    land_service: LandService = Depends()
):
    return await land_service.create_land(land_request)

@router.put("/lands/{land_id}", response_model=LandResponse)
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
    
@router.post("/lands/vegetation")
async def get_vegetation_stats(
    request: VegetationRequest
):
    get_monthly_vegetation_stats(request.coordinates, request.year)
    return {"message": "Vegetation stats generation started"}

@router.post("/lands/report")
async def get_land_analysis_report(
    request: LandAnalysisReportRequest,
    background_tasks: BackgroundTasks
):
    background_tasks.add_task(generate_land_analysis_report, request.userId, request.coordinates, request.fcm_token)
    return {"message": "Land analysis report generation started"}
