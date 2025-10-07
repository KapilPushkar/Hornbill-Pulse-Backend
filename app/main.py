from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # ADD THIS
from .api.v1.router import api_router
from .db.mongodb import db

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect_to_database()
    yield
    await db.close_database_connection()

app = FastAPI(title="Land Coordinates API", lifespan=lifespan)

# FIXED CORS CONFIGURATION
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://shiny-disco-rv4qvp5wvp93pqw7-3000.app.github.dev",  # Your exact frontend URL 
        "https://*.app.github.dev",  # Pattern for all GitHub Codespaces
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Explicit methods
    allow_headers=["*"],
)

# Add this test endpoint
@app.get("/test")
async def test_endpoint():
    return {"message": "Backend is working"}

app.include_router(api_router, prefix="/api/v1")




# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     await db.connect_to_database()
#     yield
#     await db.close_database_connection()

# app = FastAPI(title="Land Coordinates API", lifespan=lifespan)

# @app.get("/test")
# async def test_endpoint():
#     return {"message": "Backend is working"}

# # ADD CORS MIDDLEWARE BEFORE ROUTES
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         "https://*.app.github.dev",
#         "http://localhost:3000",
#         "http://127.0.0.1:3000",
#         "*"  # TEMPORARY - for debugging only
#     ],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# app.include_router(api_router, prefix="/api/v1")

