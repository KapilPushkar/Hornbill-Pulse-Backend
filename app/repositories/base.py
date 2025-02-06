from typing import Any, Dict, List, Optional
from bson import ObjectId
from pymongo import MongoClient
from ..db.mongodb import db

class BaseRepository:
    def __init__(self, collection_name: str):
        self.collection = db.db[collection_name]
        self.sync_client = MongoClient()  # Synchronous MongoDB client
        self.sync_collection = self.sync_client[db.db.name][collection_name]

    async def find_one(self, id: str) -> Optional[Dict]:
        return await self.collection.find_one({"_id": ObjectId(id)})

    async def find_many(self, query: Dict) -> List[Dict]:
        cursor = self.collection.find(query)
        return await cursor.to_list(None)

    async def create(self, data: Dict) -> Dict:
        result = await self.collection.insert_one(data)
        return await self.find_one(str(result.inserted_id))

    async def update(self, id: str, data: Dict) -> Optional[Dict]:
        await self.collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": data}
        )
        return await self.find_one(id)

    async def delete(self, id: str) -> bool:
        result = await self.collection.delete_one({"_id": ObjectId(id)})
        return result.deleted_count > 0

    def sync_update(self, id: str, data: Dict) -> Optional[Dict]:
        self.sync_collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": data}
        )
        return self.sync_collection.find_one({"_id": ObjectId(id)})
    def sync_create(self, data: Dict) -> Dict:
        result = self.sync_collection.insert_one(data)
        return self.sync_collection.find_one({"_id": result.inserted_id})