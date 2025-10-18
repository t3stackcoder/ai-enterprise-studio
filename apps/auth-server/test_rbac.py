"""
Role-Based Access Control (RBAC) tests for auth-server
Tests for different user roles and subscription tiers
"""

import sys
from pathlib import Path

# Add libs to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "libs"))

import os

import jwt
from dotenv import load_dotenv
from fastapi import status
from models.user import User

# Load environment variables
load_dotenv()


class TestUserRoles:
    """Test different user roles (user, admin, enterprise)"""

    def test_user_role_in_token(self, client, sample_user):
        """Test that user role is correctly embedded in access token"""
        username = os.getenv("TEST_USER_USERNAME", "testuser")
        password = os.getenv("TEST_USER_PASSWORD", "password123")

        response = client.post("/api/auth/login", json={"username": username, "password": password})
        assert response.status_code == status.HTTP_200_OK

        access_token = response.json()["access_token"]
        secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        payload = jwt.decode(access_token, secret_key, algorithms=[algorithm], options={"verify_aud": False})

        assert payload["role"] == "user"
        assert payload["subscription_tier"] == "free"

    def test_admin_role_in_token(self, client, admin_user):
        """Test that admin role is correctly embedded in access token"""
        username = os.getenv("TEST_ADMIN_USERNAME", "adminuser")
        password = os.getenv("TEST_ADMIN_PASSWORD", "admin123")

        response = client.post("/api/auth/login", json={"username": username, "password": password})
        assert response.status_code == status.HTTP_200_OK

        access_token = response.json()["access_token"]
        secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        payload = jwt.decode(access_token, secret_key, algorithms=[algorithm], options={"verify_aud": False})

        assert payload["role"] == "admin"
        assert payload["subscription_tier"] == "enterprise"

    def test_enterprise_role_in_token(self, client, enterprise_user):
        """Test that enterprise role is correctly embedded in access token"""
        username = os.getenv("TEST_ENTERPRISE_USERNAME", "enterpriseuser")
        password = os.getenv("TEST_ENTERPRISE_PASSWORD", "enterprise123")

        response = client.post("/api/auth/login", json={"username": username, "password": password})
        assert response.status_code == status.HTTP_200_OK

        access_token = response.json()["access_token"]
        secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        payload = jwt.decode(access_token, secret_key, algorithms=[algorithm], options={"verify_aud": False})

        assert payload["role"] == "enterprise"
        assert payload["subscription_tier"] == "enterprise"

    def test_multiple_users_different_roles(
        self, client, sample_user, admin_user, enterprise_user
    ):
        """Test that multiple users with different roles can coexist"""
        # Login as regular user
        username = os.getenv("TEST_USER_USERNAME", "testuser")
        password = os.getenv("TEST_USER_PASSWORD", "password123")
        user_response = client.post(
            "/api/auth/login", json={"username": username, "password": password}
        )
        assert user_response.status_code == status.HTTP_200_OK

        # Login as admin
        admin_username = os.getenv("TEST_ADMIN_USERNAME", "adminuser")
        admin_password = os.getenv("TEST_ADMIN_PASSWORD", "admin123")
        admin_response = client.post(
            "/api/auth/login", json={"username": admin_username, "password": admin_password}
        )
        assert admin_response.status_code == status.HTTP_200_OK

        # Login as enterprise
        enterprise_username = os.getenv("TEST_ENTERPRISE_USERNAME", "enterpriseuser")
        enterprise_password = os.getenv("TEST_ENTERPRISE_PASSWORD", "enterprise123")
        enterprise_response = client.post(
            "/api/auth/login", json={"username": enterprise_username, "password": enterprise_password}
        )
        assert enterprise_response.status_code == status.HTTP_200_OK

        # Verify each has different roles
        user_token = user_response.json()["access_token"]
        admin_token = admin_response.json()["access_token"]
        enterprise_token = enterprise_response.json()["access_token"]

        secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        algorithm = os.getenv("JWT_ALGORITHM", "HS256")

        user_payload = jwt.decode(user_token, secret_key, algorithms=[algorithm], options={"verify_aud": False})
        admin_payload = jwt.decode(admin_token, secret_key, algorithms=[algorithm], options={"verify_aud": False})
        enterprise_payload = jwt.decode(enterprise_token, secret_key, algorithms=[algorithm], options={"verify_aud": False})

        assert user_payload["role"] == "user"
        assert admin_payload["role"] == "admin"
        assert enterprise_payload["role"] == "enterprise"


class TestSubscriptionTiers:
    """Test subscription tier functionality"""

    def test_free_tier_user(self, client, sample_user):
        """Test that free tier users have correct subscription tier"""
        username = os.getenv("TEST_USER_USERNAME", "testuser")
        password = os.getenv("TEST_USER_PASSWORD", "password123")

        response = client.post("/api/auth/login", json={"username": username, "password": password})
        assert response.status_code == status.HTTP_200_OK

        access_token = response.json()["access_token"]
        secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        payload = jwt.decode(access_token, secret_key, algorithms=[algorithm], options={"verify_aud": False})

        assert payload["subscription_tier"] == "free"

    def test_enterprise_tier_user(self, client, admin_user):
        """Test that enterprise tier users have correct subscription tier"""
        username = os.getenv("TEST_ADMIN_USERNAME", "adminuser")
        password = os.getenv("TEST_ADMIN_PASSWORD", "admin123")

        response = client.post("/api/auth/login", json={"username": username, "password": password})
        assert response.status_code == status.HTTP_200_OK

        access_token = response.json()["access_token"]
        secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        payload = jwt.decode(access_token, secret_key, algorithms=[algorithm], options={"verify_aud": False})

        assert payload["subscription_tier"] == "enterprise"

    def test_new_user_defaults_to_free_tier(self, client, db_session):
        """Test that newly registered users default to free tier"""
        payload = {
            "username": "freemiumuser",
            "password": "securepass123",
            "email_address": "freemium@example.com",
            "first_name": "Freemium",
            "last_name": "User",
        }

        response = client.post("/api/auth/register", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["subscription_tier"] == "free"
        assert data["role"] == "user"

        # Verify in database
        user = db_session.query(User).filter(User.username == "freemiumuser").first()
        assert user.subscription_tier == "free"
        assert user.role == "user"


class TestRBACScenarios:
    """Test various RBAC scenarios and access control patterns"""

    def test_user_can_access_own_profile(self, authenticated_client):
        """Test that users can access their own profile"""
        client, access_token, user = authenticated_client

        response = client.get(
            "/api/auth/profile", headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user_id"] == str(user.user_id)
        assert data["username"] == user.username

    def test_admin_can_access_own_profile(self, authenticated_admin_client):
        """Test that admin users can access their own profile"""
        client, access_token, user = authenticated_admin_client

        response = client.get(
            "/api/auth/profile", headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user_id"] == str(user.user_id)
        assert data["role"] == "admin"

    def test_enterprise_can_access_own_profile(self, authenticated_enterprise_client):
        """Test that enterprise users can access their own profile"""
        client, access_token, user = authenticated_enterprise_client

        response = client.get(
            "/api/auth/profile", headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user_id"] == str(user.user_id)
        assert data["role"] == "enterprise"

    def test_token_refresh_preserves_role(self, client, admin_user):
        """Test that token refresh preserves user role"""
        username = os.getenv("TEST_ADMIN_USERNAME", "adminuser")
        password = os.getenv("TEST_ADMIN_PASSWORD", "admin123")

        # Login
        login_response = client.post(
            "/api/auth/login", json={"username": username, "password": password}
        )
        initial_tokens = login_response.json()

        # Refresh tokens
        refresh_payload = {
            "user_id": str(admin_user.user_id),
            "refresh_token": initial_tokens["refresh_token"],
        }
        refresh_response = client.post("/api/auth/refresh", json=refresh_payload)
        assert refresh_response.status_code == status.HTTP_200_OK

        new_tokens = refresh_response.json()

        # Verify role is preserved in new token
        secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        payload = jwt.decode(new_tokens["access_token"], secret_key, algorithms=[algorithm], options={"verify_aud": False})

        assert payload["role"] == "admin"
        assert payload["subscription_tier"] == "enterprise"

    def test_token_refresh_preserves_subscription_tier(self, client, sample_user):
        """Test that token refresh preserves subscription tier"""
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
        assert refresh_response.status_code == status.HTTP_200_OK

        new_tokens = refresh_response.json()

        # Verify subscription tier is preserved in new token
        secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        payload = jwt.decode(new_tokens["access_token"], secret_key, algorithms=[algorithm], options={"verify_aud": False})

        assert payload["subscription_tier"] == "free"

    def test_different_users_have_isolated_sessions(
        self, client, sample_user, admin_user, db_session
    ):
        """Test that different users have completely isolated authentication sessions"""
        # Login as regular user
        user_username = os.getenv("TEST_USER_USERNAME", "testuser")
        user_password = os.getenv("TEST_USER_PASSWORD", "password123")
        user_response = client.post(
            "/api/auth/login", json={"username": user_username, "password": user_password}
        )
        user_tokens = user_response.json()

        # Login as admin
        admin_username = os.getenv("TEST_ADMIN_USERNAME", "adminuser")
        admin_password = os.getenv("TEST_ADMIN_PASSWORD", "admin123")
        admin_response = client.post(
            "/api/auth/login", json={"username": admin_username, "password": admin_password}
        )
        admin_tokens = admin_response.json()

        # Verify they have different tokens
        assert user_tokens["access_token"] != admin_tokens["access_token"]
        assert user_tokens["refresh_token"] != admin_tokens["refresh_token"]

        # Verify each token works only for its owner
        user_profile = client.get(
            "/api/auth/profile",
            headers={"Authorization": f"Bearer {user_tokens['access_token']}"},
        )
        assert user_profile.status_code == status.HTTP_200_OK
        assert user_profile.json()["username"] == user_username

        admin_profile = client.get(
            "/api/auth/profile",
            headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
        )
        assert admin_profile.status_code == status.HTTP_200_OK
        assert admin_profile.json()["username"] == admin_username

    def test_role_information_in_profile_endpoint(self, authenticated_admin_client):
        """Test that profile endpoint returns role information"""
        client, access_token, user = authenticated_admin_client

        response = client.get(
            "/api/auth/profile", headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "role" in data
        assert data["role"] == "admin"
        assert "subscription_tier" in data
        assert data["subscription_tier"] == "enterprise"


class TestSecurityScenarios:
    """Test security-related RBAC scenarios"""

    def test_cannot_use_another_users_refresh_token(self, client, sample_user, admin_user):
        """Test that one user cannot use another user's refresh token"""
        # Login as regular user
        user_username = os.getenv("TEST_USER_USERNAME", "testuser")
        user_password = os.getenv("TEST_USER_PASSWORD", "password123")
        user_response = client.post(
            "/api/auth/login", json={"username": user_username, "password": user_password}
        )
        user_tokens = user_response.json()

        # Try to refresh with user's token but admin's user_id
        refresh_payload = {
            "user_id": str(admin_user.user_id),
            "refresh_token": user_tokens["refresh_token"],
        }
        response = client.post("/api/auth/refresh", json=refresh_payload)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_contains_user_identifier(self, client, sample_user):
        """Test that token contains unique user identifier"""
        username = os.getenv("TEST_USER_USERNAME", "testuser")
        password = os.getenv("TEST_USER_PASSWORD", "password123")

        response = client.post("/api/auth/login", json={"username": username, "password": password})
        access_token = response.json()["access_token"]

        secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        payload = jwt.decode(access_token, secret_key, algorithms=[algorithm], options={"verify_aud": False})

        assert "sub" in payload  # Subject (user_id)
        assert payload["sub"] == str(sample_user.user_id)
        assert "username" in payload
        assert payload["username"] == username

    def test_password_not_returned_in_profile(self, authenticated_client):
        """Test that password is never returned in profile endpoint"""
        client, access_token, user = authenticated_client

        response = client.get(
            "/api/auth/profile", headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "password" not in data
        assert "password_hash" not in data
        assert "refresh_token" not in data  # Also shouldn't expose refresh token

    def test_registration_does_not_return_sensitive_data(self, client):
        """Test that registration response doesn't include sensitive data"""
        payload = {
            "username": "secureuser",
            "password": "securepass123",
            "email_address": "secure@example.com",
            "first_name": "Secure",
            "last_name": "User",
        }

        response = client.post("/api/auth/register", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "password" not in data
        assert "password_hash" not in data
        assert "refresh_token" not in data
