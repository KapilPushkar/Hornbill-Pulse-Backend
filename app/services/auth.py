from typing import Optional
from fastapi import HTTPException, status
from ..repositories.user import UserRepository
from ..models.schemas.user import UserCreate, UserLogin, UserResponse, Token
from ..core.auth import verify_password, create_access_token
from datetime import timedelta

class AuthService:
    def __init__(self):
        self.user_repo = UserRepository()

    async def register_user(self, user_data: UserCreate) -> UserResponse:
        """Register a new user"""
        # Check if mobile already exists
        if await self.user_repo.mobile_exists(user_data.mobile):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mobile number already registered"
            )

        # Create user
        user_doc = await self.user_repo.create_user(user_data)
        
        # Convert to response model
        return UserResponse(
            _id=str(user_doc["_id"]),
            name=user_doc["name"],
            mobile=user_doc["mobile"],
            email=user_doc["email"],
            role=user_doc["role"],
            language=user_doc["language"],
            is_verified=user_doc["is_verified"],
            created_at=user_doc["created_at"],
            last_login=user_doc["last_login"]
        )

    async def authenticate_user(self, login_data: UserLogin) -> Token:
        """Authenticate user and return token"""
        user = await self.user_repo.get_user_by_mobile(login_data.mobile)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid mobile number or password"
            )

        if not verify_password(login_data.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid mobile number or password"
            )

        # Update last login
        await self.user_repo.update_last_login(login_data.mobile)

        # Create access token
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": user["mobile"], "role": user["role"]}, 
            expires_delta=access_token_expires
        )

        # Create user response
        user_response = UserResponse(
            _id=str(user["_id"]),
            name=user["name"],
            mobile=user["mobile"],
            email=user["email"],
            role=user["role"],
            language=user["language"],
            is_verified=user["is_verified"],
            created_at=user["created_at"],
            last_login=user["last_login"]
        )

        return Token(
            access_token=access_token,
            token_type="bearer",
            user=user_response
        )
