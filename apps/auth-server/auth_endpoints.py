"""
Authentication endpoints for VisionScope API
"""

import sys
from pathlib import Path

# Add libs to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "libs"))

from auth_dependencies import get_current_user
from auth_service import AuthService
from database import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from models.dtos.refresh_token_request_dto import RefreshTokenRequestDto
from models.dtos.token_response_dto import TokenResponseDto
from models.dtos.user_dto import UserDto
from models.dtos.user_profile_dto import UserProfileDto
from models.dtos.user_registration_dto import UserRegistrationDto
from models.user import User
from sqlalchemy.orm import Session

router = APIRouter(prefix="/auth", tags=["authentication"])


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Dependency to get AuthService instance"""
    return AuthService(db)


@router.post("/login", response_model=TokenResponseDto)
async def login(request: UserDto, auth_service: AuthService = Depends(get_auth_service)):
    """Authenticate user and return access/refresh tokens"""
    response = await auth_service.login(request)

    if not response:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password"
        )

    return response


@router.post("/register", response_model=UserProfileDto, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserRegistrationDto, auth_service: AuthService = Depends(get_auth_service)
):
    """Register new user account"""
    user = await auth_service.register(request)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email already exists"
        )

    # Create response
    return UserProfileDto.model_validate(user)


@router.post("/refresh", response_model=TokenResponseDto)
async def refresh_tokens(
    request: RefreshTokenRequestDto, auth_service: AuthService = Depends(get_auth_service)
):
    """Refresh access and refresh tokens"""
    response = await auth_service.refresh_tokens(request)

    if not response:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    return response


@router.get("/profile", response_model=UserProfileDto)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return UserProfileDto.model_validate(current_user)
