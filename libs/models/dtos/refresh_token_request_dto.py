"""
Refresh token request DTO
"""

import uuid

from pydantic import BaseModel


class RefreshTokenRequestDto(BaseModel):
    """DTO for refresh token requests"""

    user_id: uuid.UUID
    refresh_token: str
