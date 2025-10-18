"""
Authentication setup for VisionScope FastAPI app
Clean extension methods for auth configuration
"""

import os
import sys
from pathlib import Path

# Add libs to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "libs"))

from auth_endpoints import router as auth_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def setup_auth_core(app: FastAPI):
    """
    Setup core authentication - JWT, CORS, basic auth endpoints
    Call this for essential auth functionality
    """

    # CORS configuration - get allowed origins from environment
    allowed_origins = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:3000"
    ).split(",")

    # CORS configuration (equivalent to C# UseCors("AllowAll"))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include core authentication router (login, register, refresh, profile)
    app.include_router(auth_router, prefix="/api")


def setup_auth_rbac(app: FastAPI):
    """
    Setup RBAC endpoints - role-based access control examples
    Call this to add role/subscription tier enforcement examples
    """
    from auth_dependencies import AdminUser, CurrentUser, PremiumUser

    @app.get("/api/user/profile")
    async def get_user_profile(current_user: CurrentUser):
        """Protected endpoint - requires valid JWT token"""
        return {
            "user_id": str(current_user.user_id),
            "username": current_user.username,
            "role": current_user.role,
            "subscription_tier": current_user.subscription_tier,
        }

    @app.get("/api/admin/users")
    async def get_all_users(admin_user: AdminUser):
        """Admin-only endpoint - equivalent to C# [Authorize(Policy = "AdminOnly")]"""
        return {"message": "Admin access granted", "admin": admin_user.username}

    @app.post("/api/premium/ai-analysis")
    async def premium_ai_analysis(premium_user: PremiumUser):
        """Premium feature - requires premium subscription or admin role"""
        return {
            "message": "Premium AI analysis access granted",
            "user": premium_user.username,
            "tier": premium_user.subscription_tier,
        }

    @app.put("/api/test/update-user-role")
    async def update_user_role_for_testing(request_data: dict):
        """TEST ONLY: Update user role and subscription for RBAC testing"""
        from database import get_db
        from models.user import User

        db = next(get_db())
        try:
            user = db.query(User).filter(User.username == request_data["username"]).first()
            if not user:
                return {"error": "User not found"}, 404

            if "role" in request_data:
                user.role = request_data["role"]
            if "subscription_tier" in request_data:
                user.subscription_tier = request_data["subscription_tier"]

            db.commit()
            db.refresh(user)

            return {
                "message": "User updated for testing",
                "username": user.username,
                "role": user.role,
                "subscription_tier": user.subscription_tier,
            }
        finally:
            db.close()


def setup_auth_gpu_features(app: FastAPI):
    """
    Apply RBAC to actual GPU-accelerated VisionScope features
    This is where the real business model enforcement happens
    """

    # Note: This would modify existing GPU endpoints to add auth
    # For now, this is a placeholder for future implementation
    pass


# Legacy function for backward compatibility
def setup_auth_endpoints(app: FastAPI):
    """
    DEPRECATED: Use setup_auth_rbac() instead
    """
    setup_auth_rbac(app)
