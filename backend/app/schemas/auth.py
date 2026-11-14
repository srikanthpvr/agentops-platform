"""
app/schemas/auth.py
===================
Pydantic schemas for authentication endpoints.
"""

from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    """Returned on successful login or token refresh."""

    access_token: str
    token_type: str = "bearer"
    # Remaining validity in seconds (convenience field for clients)
    expires_in: int


class LoginRequest(BaseModel):
    """Credentials submitted to POST /auth/login."""

    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """Payload for POST /auth/register — creates an Org and its first User."""

    org_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    # Enforce minimum password length at the schema boundary
    password: str = Field(..., min_length=8)
