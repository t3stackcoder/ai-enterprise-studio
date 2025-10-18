"""
Token response DTO for authentication
"""

from pydantic import BaseModel


class TokenResponseDto(BaseModel):
    """DTO for authentication token responses"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 86400  # 24 hours in seconds
