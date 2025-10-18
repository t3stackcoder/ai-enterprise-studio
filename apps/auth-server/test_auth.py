"""
Authentication tests for auth-server
Tests for signup, signin, and token refresh functionality
"""

import sys
from pathlib import Path

# Add libs to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "libs"))

import os
from datetime import datetime, timedelta, UTC

import jwt
from dotenv import load_dotenv
from fastapi import status
from models.user import User

# Load environment variables
load_dotenv()


class TestUserRegistration:
    """Test user registration (signup) functionality"""

    def test_register_new_user_success(self, client, db_session):
        """Test successful user registration"""
        payload = {
            "username": "newuser",
            "password": "securepass123",
            "email_address": "newuser@example.com",
            "first_name": "New",
            "last_name": "User",
        }

        response = client.post("/api/auth/register", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email_address"] == "newuser@example.com"
        assert data["first_name"] == "New"
        assert data["last_name"] == "User"
        assert data["role"] == "user"
        assert data["subscription_tier"] == "free"
        assert "password" not in data
        assert "password_hash" not in data

        # Verify user was created in database
        user = db_session.query(User).filter(User.username == "newuser").first()
        assert user is not None
        assert user.email_address == "newuser@example.com"

    def test_register_duplicate_username(self, client, sample_user):
        """Test registration fails with duplicate username"""
        username = os.getenv("TEST_USER_USERNAME", "testuser")
        payload = {
            "username": username,
            "password": "differentpass",
            "email_address": "different@example.com",
            "first_name": "Different",
            "last_name": "User",
        }

        response = client.post("/api/auth/register", json=payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"].lower()

    def test_register_duplicate_email(self, client, sample_user):
        """Test registration fails with duplicate email"""
        email = os.getenv("TEST_USER_EMAIL", "test@example.com")
        payload = {
            "username": "differentuser",
            "password": "securepass123",
            "email_address": email,
            "first_name": "Different",
            "last_name": "User",
        }

        response = client.post("/api/auth/register", json=payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"].lower()

    def test_register_missing_required_fields(self, client):
        """Test registration fails with missing required fields"""
        payload = {
            "username": "newuser",
            # Missing password, email, etc.
        }

        response = client.post("/api/auth/register", json=payload)

        assert response.status_code == 422

    def test_register_invalid_email_format(self, client):
        """Test registration fails with invalid email format"""
        payload = {
            "username": "newuser",
            "password": "securepass123",
            "email_address": "not-an-email",
            "first_name": "New",
            "last_name": "User",
        }

        response = client.post("/api/auth/register", json=payload)

        # Should fail validation
        assert response.status_code == 422


class TestUserLogin:
    """Test user login (signin) functionality"""

    def test_login_success(self, client, sample_user):
        """Test successful login with valid credentials"""
        username = os.getenv("TEST_USER_USERNAME", "testuser")
        password = os.getenv("TEST_USER_PASSWORD", "password123")

        response = client.post("/api/auth/login", json={"username": username, "password": password})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "expires_in" in data
        assert data["expires_in"] > 0

    def test_login_invalid_username(self, client, sample_user):
        """Test login fails with invalid username"""
        response = client.post(
            "/api/auth/login", json={"username": "nonexistent", "password": "password123"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "invalid" in response.json()["detail"].lower()

    def test_login_invalid_password(self, client, sample_user):
        """Test login fails with invalid password"""
        username = os.getenv("TEST_USER_USERNAME", "testuser")

        response = client.post(
            "/api/auth/login", json={"username": username, "password": "wrongpassword"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "invalid" in response.json()["detail"].lower()

    def test_login_updates_last_login(self, client, db_session, sample_user):
        """Test that login updates the last_login timestamp"""
        username = os.getenv("TEST_USER_USERNAME", "testuser")
        password = os.getenv("TEST_USER_PASSWORD", "password123")

        # Record time before login (timezone-aware)
        before_login = datetime.now(UTC)

        response = client.post("/api/auth/login", json={"username": username, "password": password})

        assert response.status_code == status.HTTP_200_OK

        # Refresh user from database
        db_session.refresh(sample_user)

        # Verify last_login was updated
        assert sample_user.last_login is not None
        # Convert last_login to timezone-aware if it's naive
        if sample_user.last_login.tzinfo is None:
            last_login_aware = sample_user.last_login.replace(tzinfo=UTC)
        else:
            last_login_aware = sample_user.last_login
        assert last_login_aware >= before_login

    def test_login_missing_credentials(self, client):
        """Test login fails with missing credentials"""
        response = client.post("/api/auth/login", json={})

        assert response.status_code == 422  # Unprocessable Content


class TestAccessToken:
    """Test access token generation and validation"""

    def test_access_token_contains_user_info(self, client, sample_user):
        """Test that access token contains correct user information"""
        username = os.getenv("TEST_USER_USERNAME", "testuser")
        password = os.getenv("TEST_USER_PASSWORD", "password123")

        response = client.post("/api/auth/login", json={"username": username, "password": password})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        access_token = data["access_token"]

        # Decode token without verification to inspect payload
        secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        payload = jwt.decode(
            access_token, secret_key, algorithms=[algorithm], options={"verify_aud": False}
        )

        assert payload["username"] == username
        assert payload["role"] == "user"
        assert payload["subscription_tier"] == "free"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
        assert "sub" in payload  # User ID

    def test_access_token_expiration(self, client, sample_user):
        """Test that access token has correct expiration time"""
        username = os.getenv("TEST_USER_USERNAME", "testuser")
        password = os.getenv("TEST_USER_PASSWORD", "password123")

        response = client.post("/api/auth/login", json={"username": username, "password": password})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        access_token = data["access_token"]

        # Decode token
        secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        payload = jwt.decode(
            access_token, secret_key, algorithms=[algorithm], options={"verify_aud": False}
        )

        # Check expiration is in the future
        exp_timestamp = payload["exp"]
        iat_timestamp = payload["iat"]
        assert exp_timestamp > iat_timestamp

        # Check expiration is approximately 24 hours (1440 minutes)
        expected_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
        actual_minutes = (exp_timestamp - iat_timestamp) / 60
        assert abs(actual_minutes - expected_minutes) < 1  # Allow 1 minute variance

    def test_authenticated_endpoint_with_valid_token(self, authenticated_client):
        """Test accessing protected endpoint with valid access token"""
        client, access_token, user = authenticated_client

        response = client.get(
            "/api/auth/profile", headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == user.username
        assert data["email_address"] == user.email_address

    def test_authenticated_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token fails"""
        response = client.get("/api/auth/profile")

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_authenticated_endpoint_with_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token fails"""
        response = client.get(
            "/api/auth/profile", headers={"Authorization": "Bearer invalid_token_here"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestRefreshToken:
    """Test refresh token functionality"""

    def test_refresh_token_generation(self, client, sample_user, db_session):
        """Test that login generates and stores refresh token"""
        username = os.getenv("TEST_USER_USERNAME", "testuser")
        password = os.getenv("TEST_USER_PASSWORD", "password123")

        response = client.post("/api/auth/login", json={"username": username, "password": password})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        refresh_token = data["refresh_token"]

        assert refresh_token is not None
        assert len(refresh_token) > 0

        # Verify refresh token is stored in database
        db_session.refresh(sample_user)
        assert sample_user.refresh_token == refresh_token
        assert sample_user.refresh_token_expiry_time is not None

    def test_refresh_token_success(self, client, sample_user):
        """Test successful token refresh with valid refresh token"""
        username = os.getenv("TEST_USER_USERNAME", "testuser")
        password = os.getenv("TEST_USER_PASSWORD", "password123")

        # Login to get initial tokens
        login_response = client.post(
            "/api/auth/login", json={"username": username, "password": password}
        )
        assert login_response.status_code == status.HTTP_200_OK
        initial_tokens = login_response.json()

        # Small delay to ensure different iat timestamp
        import time

        time.sleep(1)

        # Refresh tokens
        refresh_payload = {
            "user_id": str(sample_user.user_id),
            "refresh_token": initial_tokens["refresh_token"],
        }
        refresh_response = client.post("/api/auth/refresh", json=refresh_payload)

        assert refresh_response.status_code == status.HTTP_200_OK
        new_tokens = refresh_response.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        assert "expires_in" in new_tokens

        # Verify tokens are different from initial ones
        # Note: Access token will be different due to different iat timestamp
        # Refresh token should also be different
        assert new_tokens["refresh_token"] != initial_tokens["refresh_token"]

    def test_refresh_token_invalid_token(self, client, sample_user):
        """Test refresh fails with invalid refresh token"""
        refresh_payload = {
            "user_id": str(sample_user.user_id),
            "refresh_token": "invalid_refresh_token",
        }
        response = client.post("/api/auth/refresh", json=refresh_payload)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "invalid" in response.json()["detail"].lower()

    def test_refresh_token_invalid_user_id(self, client, sample_user):
        """Test refresh fails with invalid user_id"""
        username = os.getenv("TEST_USER_USERNAME", "testuser")
        password = os.getenv("TEST_USER_PASSWORD", "password123")

        # Login to get valid refresh token
        login_response = client.post(
            "/api/auth/login", json={"username": username, "password": password}
        )
        initial_tokens = login_response.json()

        # Try to refresh with wrong user_id
        refresh_payload = {
            "user_id": "00000000-0000-0000-0000-000000000000",
            "refresh_token": initial_tokens["refresh_token"],
        }
        response = client.post("/api/auth/refresh", json=refresh_payload)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token_expired(self, client, sample_user, db_session):
        """Test refresh fails with expired refresh token"""
        username = os.getenv("TEST_USER_USERNAME", "testuser")
        password = os.getenv("TEST_USER_PASSWORD", "password123")

        # Login to get refresh token
        login_response = client.post(
            "/api/auth/login", json={"username": username, "password": password}
        )
        initial_tokens = login_response.json()

        # Manually expire the refresh token in database
        sample_user.refresh_token_expiry_time = datetime.now(UTC) - timedelta(days=1)
        db_session.commit()

        # Try to refresh with expired token
        refresh_payload = {
            "user_id": str(sample_user.user_id),
            "refresh_token": initial_tokens["refresh_token"],
        }
        response = client.post("/api/auth/refresh", json=refresh_payload)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token_can_access_protected_endpoint(self, client, sample_user):
        """Test that new access token from refresh works on protected endpoints"""
        username = os.getenv("TEST_USER_USERNAME", "testuser")
        password = os.getenv("TEST_USER_PASSWORD", "password123")

        # Login
        login_response = client.post(
            "/api/auth/login", json={"username": username, "password": password}
        )
        initial_tokens = login_response.json()

        # Refresh tokens
        refresh_payload = {
            "user_id": str(sample_user.user_id),
            "refresh_token": initial_tokens["refresh_token"],
        }
        refresh_response = client.post("/api/auth/refresh", json=refresh_payload)
        new_tokens = refresh_response.json()

        # Use new access token to access protected endpoint
        profile_response = client.get(
            "/api/auth/profile", headers={"Authorization": f"Bearer {new_tokens['access_token']}"}
        )

        assert profile_response.status_code == status.HTTP_200_OK
        data = profile_response.json()
        assert data["username"] == username
