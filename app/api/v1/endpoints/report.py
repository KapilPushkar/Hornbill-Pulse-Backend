from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from ....models.schemas.land import LandAnalysisReportRequest
from ....services.land_vegetation import generate_land_analysis_report
from ....services.land import LandService

router = APIRouter()

@router.post("/vegetation/{land_id}", description="Generate vegetation analysis report")
async def generate_vegetation_report(
    land_id: str,
    background_tasks: BackgroundTasks,
    land_service: LandService = Depends()
):
    land = await land_service.get_land(land_id)
    if not land:
        raise HTTPException(status_code=404, detail="Land not found")

    # Add async task
    background_tasks.add_task(
        generate_land_analysis_report,
        land.user_id,
        land_id,  # Pass land_id to store with stats
        land.coordinates
    )
    
    return {
        "message": "Vegetation analysis report generation started",
        "land_id": land_id,
        "status": "processing"
    }
