"""
app/schemas/trace.py
====================
Pydantic schemas for trace ingestion and retrieval endpoints.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Span schemas
# ---------------------------------------------------------------------------

class SpanCreate(BaseModel):
    """Single span submitted as part of a trace ingestion payload."""

    # Callers may supply their own deterministic UUID for idempotency
    id: uuid.UUID | None = None
    name: str = Field(..., min_length=1, max_length=255)
    span_type: str = Field(default="custom")
    input: str | None = None          # noqa: A003 – matches JSON field name
    output: str | None = None         # noqa: A003
    model: str | None = None
    tokens_input: int = Field(default=0, ge=0)
    tokens_output: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0.0)
    latency_ms: float | None = None
    started_at: datetime
    ended_at: datetime | None = None
    error: str | None = None
    metadata: dict | None = None      # noqa: A003
    parent_span_id: uuid.UUID | None = None


class SpanResponse(BaseModel):
    """Serialised Span returned to callers."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    trace_id: uuid.UUID
    parent_span_id: uuid.UUID | None
    name: str
    span_type: str
    input: str | None = Field(None, alias="input_")       # ORM attr → JSON key
    output: str | None = Field(None, alias="output_")
    model: str | None
    tokens_input: int
    tokens_output: int
    cost_usd: float
    latency_ms: float | None
    started_at: datetime
    ended_at: datetime | None
    error: str | None
    metadata: dict | None = Field(None, alias="metadata_")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ---------------------------------------------------------------------------
# Trace schemas
# ---------------------------------------------------------------------------

class TraceCreate(BaseModel):
    """Payload for POST /ingest/traces.

    Callers may embed all spans directly so the entire trace can be
    written atomically in a single database transaction.
    """

    # Callers may supply their own UUID for idempotency
    id: uuid.UUID | None = None
    session_id: str | None = None
    agent_name: str = Field(..., min_length=1, max_length=255)
    started_at: datetime
    metadata: dict | None = None      # noqa: A003
    spans: list[SpanCreate] = Field(default_factory=list)


class TraceResponse(BaseModel):
    """Serialised Trace returned to callers."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    session_id: str | None
    agent_name: str
    status: str
    duration_ms: float | None
    total_tokens: int
    total_cost_usd: float
    metadata: dict | None = Field(None, alias="metadata_")
    started_at: datetime
    ended_at: datetime | None
    created_at: datetime
    # Convenience field — number of child spans (may be 0 on list endpoints)
    span_count: int = 0
    spans: list[SpanResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TraceUpdate(BaseModel):
    """Partial update payload for PATCH /traces/{trace_id}."""

    status: str | None = None
    ended_at: datetime | None = None
    total_tokens: int | None = Field(None, ge=0)
    total_cost_usd: float | None = Field(None, ge=0.0)
