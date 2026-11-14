"""
app/schemas/governance.py
=========================
Pydantic schemas for governance policy and audit log endpoints.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Policy schemas
# ---------------------------------------------------------------------------

class PolicyCreate(BaseModel):
    """Payload for creating a new governance policy."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    # Flexible rule DSL – validated by the policy engine at evaluation time
    rules: dict
    # Action taken when the policy triggers: "log" | "block" | "alert"
    action: str = Field(default="log")


class PolicyUpdate(BaseModel):
    """Partial update payload for PATCH /policies/{policy_id}."""

    name: str | None = Field(None, min_length=1, max_length=255)
    rules: dict | None = None
    action: str | None = None
    is_enabled: bool | None = None


class PolicyResponse(BaseModel):
    """Serialised Policy returned to callers."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str | None
    rules: dict
    action: str
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# AuditLog schemas
# ---------------------------------------------------------------------------

class AuditLogResponse(BaseModel):
    """Serialised AuditLog returned to callers."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    trace_id: uuid.UUID | None
    policy_id: uuid.UUID | None
    violation_type: str
    severity: str
    payload: dict
    created_at: datetime
