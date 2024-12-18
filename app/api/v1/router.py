from fastapi import APIRouter
from .endpoints import land

api_router = APIRouter()
api_router.include_router(land.router, tags=["lands"]) 