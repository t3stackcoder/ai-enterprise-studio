"""
Video Analysis Service - FastAPI Server
Handles AI-powered video analysis using GPU-accelerated models
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / ".env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI application"""
    logger.info("🚀 Starting Video Analysis Server...")
    logger.info("📦 Loading AI models...")

    # TODO: Pre-load models here for faster inference
    # from gpu.models import load_models
    # await load_models()

    logger.info("✅ Video Analysis Server ready!")
    yield
    logger.info("🛑 Shutting down Video Analysis Server...")


# Create FastAPI app
app = FastAPI(
    title="Video Analysis Service",
    description="AI-powered video analysis using GPU-accelerated models",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3002").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "video-analysis-server",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "video-analysis-server"
    }


@app.get("/api/models")
async def list_models():
    """List available AI models"""
    return {
        "models": [
            {
                "name": "CLIP Visual Intelligence",
                "type": "visual_understanding",
                "status": "available"
            },
            {
                "name": "Emotion Detection",
                "type": "text_emotion",
                "status": "available"
            },
            {
                "name": "Face Expression",
                "type": "visual_emotion",
                "status": "available"
            },
            {
                "name": "MediaPipe Pose",
                "type": "pose_detection",
                "status": "available"
            },
            {
                "name": "Scene Detection",
                "type": "video_segmentation",
                "status": "available"
            }
        ]
    }


if __name__ == "__main__":
    port = int(os.getenv("VIDEO_ANALYSIS_PORT", "8002"))
    host = os.getenv("VIDEO_ANALYSIS_HOST", "0.0.0.0")

    logger.info(f"🎬 Starting server on {host}:{port}")

    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
