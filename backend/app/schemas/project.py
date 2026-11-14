"""
app/schemas/project.py
======================
Pydantic schemas for Project and API Key endpoints.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Project schemas
# ---------------------------------------------------------------------------

class ProjectCreate(BaseModel):
    """Payload for creating a new Project."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class ProjectResponse(BaseModel):
    """Serialised Project returned to callers."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime


# ---------------------------------------------------------------------------
# API Key schemas
# ---------------------------------------------------------------------------

class APIKeyCreate(BaseModel):
    """Payload for creating a new API key."""

    name: str = Field(..., min_length=1, max_length=255)


class APIKeyResponse(BaseModel):
    """Serialised API Key (never includes the full key)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    key_prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None


class APIKeyCreatedResponse(APIKeyResponse):
    """Extended response shown ONCE immediately after key creation.

    ``full_key`` is the only time the plaintext key is transmitted.
    It MUST be displayed to the user immediately and cannot be retrieved
    again — only the hash is stored server-side.
    """

    full_key: str
