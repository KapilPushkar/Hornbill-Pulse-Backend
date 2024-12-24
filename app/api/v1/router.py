from fastapi import APIRouter
from .endpoints import land, report

api_router = APIRouter()
api_router.include_router(land.router, prefix="/lands", tags=["lands"])
api_router.include_router(report.router, prefix="/reports", tags=["reports"]) 