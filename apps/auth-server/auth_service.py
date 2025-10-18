"""
Authentication service for VisionScope
"""

import os
import secrets
import sys
from datetime import datetime, timedelta, UTC
from pathlib import Path

# Add libs to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "libs"))

import bcrypt
import jwt
from models.dtos.refresh_token_request_dto import RefreshTokenRequestDto
from models.dtos.token_response_dto import TokenResponseDto
from models.dtos.user_dto import UserDto
from models.dtos.user_registration_dto import UserRegistrationDto
from models.user import User
from sqlalchemy.orm import Session


class AuthService:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 1440  # 24 hours
        self.refresh_token_expire_days = 30

    async def login(self, request: UserDto) -> TokenResponseDto | None:
        """Authenticate user and return tokens"""
        user = self.db.query(User).filter(User.username == request.username).first()

        if not user:
            return None

        if not self._verify_password(request.password, user.password_hash):
            return None

        # Update last login
        user.last_login = datetime.now(UTC)
        self.db.commit()

        return await self._create_token_response(user)

    async def register(self, request: UserRegistrationDto) -> User | None:
        """Register new user"""
        # Check if username or email already exists
        existing_user = (
            self.db.query(User)
            .filter(
                (User.username == request.username) | (User.email_address == request.email_address)
            )
            .first()
        )

        if existing_user:
            return None

        # Hash the password
        password_hash = self._hash_password(request.password)

        # Create new user
        user = User(
            username=request.username,
            password_hash=password_hash,
            email_address=request.email_address,
            first_name=request.first_name,
            last_name=request.last_name,
            role="user",
            subscription_tier="free",
            created_at=datetime.now(UTC),
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user

    async def refresh_tokens(self, request: RefreshTokenRequestDto) -> TokenResponseDto | None:
        """Refresh access and refresh tokens"""
        user = await self._validate_refresh_token(request.user_id, request.refresh_token)

        if not user:
            return None

        return await self._create_token_response(user)

    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))

    def _create_access_token(self, user: User) -> str:
        """Create JWT access token"""
        payload = {
            "sub": str(user.user_id),
            "username": user.username,
            "role": user.role,
            "subscription_tier": user.subscription_tier,
            "exp": datetime.now(UTC) + timedelta(minutes=self.access_token_expire_minutes),
            "iat": datetime.now(UTC),
            "iss": os.getenv("JWT_ISSUER", "visionscope-api"),
            "aud": os.getenv("JWT_AUDIENCE", "visionscope-users"),
            "type": "access",
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def _generate_refresh_token(self) -> str:
        """Generate secure refresh token"""
        return secrets.token_urlsafe(32)

    async def _create_token_response(self, user: User) -> TokenResponseDto:
        """Create complete token response"""
        access_token = self._create_access_token(user)
        refresh_token = await self._generate_and_save_refresh_token(user)

        return TokenResponseDto(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.access_token_expire_minutes * 60,
        )

    async def _generate_and_save_refresh_token(self, user: User) -> str:
        """Generate and save refresh token to user"""
        refresh_token = self._generate_refresh_token()

        user.refresh_token = refresh_token
        user.refresh_token_expiry_time = datetime.now(UTC) + timedelta(
            days=self.refresh_token_expire_days
        )

        self.db.commit()
        return refresh_token

    async def _validate_refresh_token(self, user_id: str, refresh_token: str) -> User | None:
        """Validate refresh token and return user if valid"""
        user = self.db.query(User).filter(User.user_id == user_id).first()

        if not user:
            return None

        if user.refresh_token != refresh_token:
            return None

        if user.refresh_token_expiry_time:
            # Handle timezone-naive datetime from database
            if user.refresh_token_expiry_time.tzinfo is None:
                expiry_aware = user.refresh_token_expiry_time.replace(tzinfo=UTC)
            else:
                expiry_aware = user.refresh_token_expiry_time

            if expiry_aware < datetime.now(UTC):
                return None

        return user

    def verify_access_token(self, token: str) -> dict | None:
        """Verify and decode access token"""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                issuer=os.getenv("JWT_ISSUER", "visionscope-api"),
                audience=os.getenv("JWT_AUDIENCE", "visionscope-users"),
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_iss": True,
                    "verify_aud": True,
                },
            )

            if payload.get("type") != "access":
                return None

            return payload
        except jwt.PyJWTError:
            return None
