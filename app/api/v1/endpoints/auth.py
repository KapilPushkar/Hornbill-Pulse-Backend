from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List
from ....models.schemas.user import UserCreate, UserLogin, UserResponse, Token, UserRole
from ....services.auth import AuthService
from ....core.auth import verify_token
from ....repositories.user import UserRepository

router = APIRouter()
security = HTTPBearer()

# Dependency to get current user from token
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get current user from JWT token"""
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    mobile = payload.get("sub")
    if mobile is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    user_repo = UserRepository()
    user = await user_repo.get_user_by_mobile(mobile)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user

# Role-based access control decorator
def require_role(allowed_roles: List[UserRole]):
    """Decorator to require specific roles"""
    async def role_checker(current_user: dict = Depends(get_current_user)):
        user_role = current_user.get("role")
        if user_role not in [role.value for role in allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker

@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    auth_service: AuthService = Depends()
):
    """Register a new user (farmer, agent, or admin)"""
    try:
        user = await auth_service.register_user(user_data)
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/login", response_model=Token)
async def login_user(
    login_data: UserLogin,
    auth_service: AuthService = Depends()
):
    """Login user and return JWT token"""
    try:
        token = await auth_service.authenticate_user(login_data)
        return token
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

@router.get("/profile", response_model=UserResponse)
async def get_user_profile(
    current_user: dict = Depends(get_current_user)
):
    """Get current user profile (requires authentication)"""
    return UserResponse(
        _id=str(current_user["_id"]),
        name=current_user["name"],
        mobile=current_user["mobile"],
        email=current_user["email"],
        role=current_user["role"],
        language=current_user["language"],
        is_verified=current_user["is_verified"],
        created_at=current_user["created_at"],
        last_login=current_user["last_login"],
        photo_url=current_user.get("photo_url"),
        gender=current_user.get("gender"),
        age_bracket=current_user.get("age_bracket")
    )

@router.get("/admin-only")
async def admin_only_endpoint(
    current_user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """Test endpoint - only admins can access"""
    return {"message": "Hello Admin!", "user": current_user["name"]}

@router.get("/agent-admin")
async def agent_admin_endpoint(
    current_user: dict = Depends(require_role([UserRole.AGENT, UserRole.ADMIN]))
):
    """Test endpoint - agents and admins can access"""
    return {"message": "Hello Agent/Admin!", "user": current_user["name"]}

@router.get("/all-users")
async def all_users_endpoint(
    current_user: dict = Depends(require_role([UserRole.FARMER, UserRole.AGENT, UserRole.ADMIN]))
):
    """Test endpoint - all authenticated users can access"""
    return {"message": f"Hello {current_user['role']}!", "user": current_user["name"]}
