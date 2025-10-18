"""
User DTO for authentication requests
"""

from pydantic import BaseModel


class UserDto(BaseModel):
    """DTO for user authentication requests"""

    username: str
    password: str
