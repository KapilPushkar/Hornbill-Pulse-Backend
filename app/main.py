from contextlib import asynccontextmanager
from fastapi import FastAPI
from .api.v1.router import api_router
from .db.mongodb import db

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect_to_database()
    yield
    await db.close_database_connection()

app = FastAPI(title="Land Coordinates API", lifespan=lifespan)

app.include_router(api_router, prefix="/api/v1")