"""
User profile DTO
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserProfileDto(BaseModel):
    """DTO for user profile responses (no sensitive data)"""

    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    username: str
    email_address: str
    first_name: str | None = None
    last_name: str | None = None
    role: str
    subscription_tier: str
    created_at: datetime
    last_login: datetime | None = None
