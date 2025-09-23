from typing import Optional, List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from ..db.mongodb import db
from ..models.schemas.user import UserCreate, UserResponse, UserRole
from ..core.auth import get_password_hash
from datetime import datetime

class UserRepository:
    def __init__(self):
        self.collection: AsyncIOMotorCollection = db.get_collection("users")

    async def create_user(self, user_data: UserCreate) -> dict:
        """Create a new user"""
        # Hash password
        hashed_password = get_password_hash(user_data.password)
        
        # Prepare user document
        user_doc = {
            "mobile": user_data.mobile,
            "name": user_data.name,
            "role": user_data.role.value,
            "password_hash": hashed_password,
            "email": user_data.email,
            "language": user_data.language,
            "is_verified": False,
            "created_at": datetime.utcnow(),
            "last_login": None,
            "photo_url": None,
            "gender": None,
            "age_bracket": None
        }
        
        result = await self.collection.insert_one(user_doc)
        user_doc["_id"] = result.inserted_id
        return user_doc

    async def get_user_by_mobile(self, mobile: str) -> Optional[dict]:
        """Get user by mobile number"""
        return await self.collection.find_one({"mobile": mobile})

    async def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """Get user by ID"""
        return await self.collection.find_one({"_id": ObjectId(user_id)})

    async def update_last_login(self, mobile: str):
        """Update user's last login time"""
        await self.collection.update_one(
            {"mobile": mobile},
            {"$set": {"last_login": datetime.utcnow()}}
        )

    async def mobile_exists(self, mobile: str) -> bool:
        """Check if mobile number already exists"""
        user = await self.collection.find_one({"mobile": mobile})
        return user is not None
