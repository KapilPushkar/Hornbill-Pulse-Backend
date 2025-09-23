from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from enum import Enum
from datetime import datetime

class UserRole(str, Enum):
    FARMER = "farmer"
    AGENT = "agent"
    ADMIN = "admin"

class UserCreate(BaseModel):
    mobile: str = Field(..., min_length=10, max_length=15)
    name: str = Field(..., min_length=2, max_length=100)
    role: UserRole = UserRole.FARMER
    password: str = Field(..., min_length=6)
    email: Optional[EmailStr] = None
    language: str = Field(default="en")

class UserLogin(BaseModel):
    mobile: str = Field(..., min_length=10, max_length=15)
    password: str = Field(..., min_length=6)

class UserProfile(BaseModel):
    name: str
    mobile: str
    email: Optional[str] = None
    role: UserRole
    language: str
    photo_url: Optional[str] = None
    gender: Optional[str] = None
    age_bracket: Optional[str] = None
    is_verified: bool = Field(default=False)

class UserResponse(UserProfile):
    id: str = Field(..., alias="_id")
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        populate_by_name = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse
