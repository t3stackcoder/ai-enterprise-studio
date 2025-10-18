"""
Auth Server - FastAPI application for authentication and authorization
"""

import sys
from pathlib import Path

# Add libs to Python path so we can import from models, buildingblocks, etc.
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "libs"))

import logging
import os

import uvicorn
from auth_setup import setup_auth_core, setup_auth_rbac
from database import close_db, init_db
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AI Enterprise Studio - Auth API",
    description="Authentication and authorization service with JWT and RBAC",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 Starting Auth Server...")

    # Initialize database
    init_db()

    logger.info("✅ Auth Server ready!")
    logger.info("📚 API Docs: http://localhost:8000/api/docs")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("👋 Shutting down Auth Server...")
    close_db()
    logger.info("✅ Shutdown complete")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "auth-server", "version": "1.0.0"}


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "AI Enterprise Studio - Auth API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/health",
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle uncaught exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500, content={"detail": "Internal server error", "type": type(exc).__name__}
    )


# Setup authentication features using extension methods
setup_auth_core(app)  # Essential: JWT, CORS, login/register/refresh
setup_auth_rbac(app)  # Optional: RBAC examples and protected endpoints


# Run server
if __name__ == "__main__":
    port = int(os.getenv("AUTH_SERVER_PORT", "8000"))
    host = os.getenv("AUTH_SERVER_HOST", "0.0.0.0")

    logger.info(f"🌐 Starting server on {host}:{port}")

    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        reload=True,  # Auto-reload on code changes (development only)
        log_level="info",
    )
