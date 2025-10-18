"""
User registration DTO
"""

from pydantic import BaseModel, EmailStr


class UserRegistrationDto(BaseModel):
    """DTO for user registration"""

    username: str
    password: str
    email_address: EmailStr
    first_name: str | None = None
    last_name: str | None = None
