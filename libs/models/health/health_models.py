"""
Health domain models - centralized in models folder
"""

from pydantic import BaseModel


class GetHealthResponse(BaseModel):
    """Response model for health check"""

    status: str
    gpu_available: bool
    gpu_name: str
    device: str
    app_name: str
    version: str
