from motor.motor_asyncio import AsyncIOMotorClient
from ..core.config import settings

class MongoDB:
    client = None
    db = None

    async def connect_to_database(self):
        self.client = AsyncIOMotorClient(settings.MONGO_URI)
        self.db = self.client[settings.DATABASE_NAME]

    async def close_database_connection(self):
        if self.client:
            self.client.close()

db = MongoDB() 