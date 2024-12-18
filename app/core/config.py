from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    MONGO_URI: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "land_coordinates_db"
    API_V1_STR: str = "/api/v1"
    
    CDSE_USERNAME: str
    CDSE_PASSWORD: str
    CDSE_CLIENT_ID: str = "cdse-public"
    CDSE_BASE_URL: str = "https://catalogue.dataspace.copernicus.eu/odata/v1"
    CDSE_TOKEN_URL: str = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    CDSE_S3_URL: str = "https://eodata.dataspace.copernicus.eu"
    CDSE_S3_ACCESS_KEY: str
    CDSE_S3_SECRET_KEY: str

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings() 