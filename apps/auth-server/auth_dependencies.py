"""
Authentication and authorization configuration for VisionScope API
"""

import os
import sys
from pathlib import Path
from typing import Annotated

# Add libs to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "libs"))

import jwt
from database import get_db
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from models.user import User
from sqlalchemy.orm import Session

# Security scheme for JWT tokens
security = HTTPBearer()


class AuthConfig:
    """Authentication configuration"""

    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours
    ISSUER = os.getenv("JWT_ISSUER", "visionscope-api")
    AUDIENCE = os.getenv("JWT_AUDIENCE", "visionscope-users")


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Verify JWT token and return payload
    Equivalent to C# JWT token validation parameters
    """
    try:
        payload = jwt.decode(
            credentials.credentials,
            AuthConfig.SECRET_KEY,
            algorithms=[AuthConfig.ALGORITHM],
            issuer=AuthConfig.ISSUER,
            audience=AuthConfig.AUDIENCE,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_iss": True,
                "verify_aud": True,
            },
        )

        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )

        return payload

    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
        ) from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from e


def get_current_user(
    token_payload: dict = Depends(verify_token), db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from token
    """
    user_id = token_payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


def require_role(required_role):
    """
    Role-based authorization decorator
    Equivalent to C# [Authorize(Roles = "Admin")] or policy-based auth
    """

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        # Handle both single role and list of roles
        if isinstance(required_role, list):
            if current_user.role not in required_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requires one of: {', '.join(required_role)} role",
                )
        else:
            if current_user.role != required_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail=f"Requires {required_role} role"
                )
        return current_user

    return role_checker


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Admin-only authorization
    Equivalent to C# "AdminOnly" policy
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def require_premium_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Premium or Admin access required
    VisionScope-specific authorization for premium features
    """
    if (
        current_user.subscription_tier not in ["premium", "enterprise"]
        and current_user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription or admin access required",
        )
    return current_user


# Dependency aliases for cleaner endpoint definitions
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]
PremiumUser = Annotated[User, Depends(require_premium_or_admin)]
