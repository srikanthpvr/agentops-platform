"""
agentops.models
===============
Pydantic data models used for serialising traces and spans before sending to
the AgentOps backend API, plus the SDK configuration model.

All models use Pydantic v2 semantics (model_config, model_dump, etc.).
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# SDK configuration
# ---------------------------------------------------------------------------

class SDKConfig(BaseModel):
    """
    Immutable configuration snapshot for the AgentOps SDK.

    Values can be sourced from keyword arguments to :func:`agentops.init` or
    from environment variables (env-vars take lower precedence than explicit
    kwargs so callers can always override).
    """

    api_key: str = Field(
        description="AgentOps API key (required). "
        "Falls back to AGENTOPS_API_KEY env-var when not supplied explicitly.",
    )
    base_url: str = Field(
        default="https://api.agentops.io",
        description="Base URL of the AgentOps ingest endpoint.",
    )
    timeout: float = Field(
        default=30.0,
        gt=0,
        description="HTTP request timeout in seconds.",
    )
    batch_size: int = Field(
        default=10,
        ge=1,
        description="Maximum number of traces to buffer before an automatic flush.",
    )
    flush_interval: float = Field(
        default=5.0,
        gt=0,
        description="Interval in seconds between automatic background flushes.",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum number of HTTP retry attempts with exponential back-off.",
    )
    debug: bool = Field(
        default=False,
        description="When True, the SDK emits verbose DEBUG-level log messages.",
    )

    model_config = {"frozen": True}  # treat config as immutable after creation

    @model_validator(mode="before")
    @classmethod
    def _apply_env_vars(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment-variable defaults for fields not explicitly provided.
        Explicit kwargs always win; env-vars are only used as fallbacks.
        """
        env_map = {
            "api_key": "AGENTOPS_API_KEY",
            "base_url": "AGENTOPS_BASE_URL",
            "timeout": "AGENTOPS_TIMEOUT",
            "batch_size": "AGENTOPS_BATCH_SIZE",
            "flush_interval": "AGENTOPS_FLUSH_INTERVAL",
            "debug": "AGENTOPS_DEBUG",
        }
        for field_name, env_var in env_map.items():
            if field_name not in values or values[field_name] is None:
                env_value = os.environ.get(env_var)
                if env_value is not None:
                    values[field_name] = env_value
        return values

    @field_validator("api_key")
    @classmethod
    def _validate_api_key(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError(
                "AgentOps API key must not be empty. "
                "Pass api_key= to agentops.init() or set the AGENTOPS_API_KEY environment variable."
            )
        return v.strip()

    @field_validator("base_url")
    @classmethod
    def _validate_base_url(cls, v: str) -> str:
        v = v.rstrip("/")
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"base_url must start with http:// or https://; got: {v!r}")
        return v


# ---------------------------------------------------------------------------
# Span data
# ---------------------------------------------------------------------------

class SpanData(BaseModel):
    """
    Wire-format model for a single span within a trace.

    Spans represent discrete sub-operations (LLM calls, tool invocations,
    retrieval steps, etc.) nested inside a parent :class:`TraceData`.
    """

    span_id: str = Field(description="UUID4 string uniquely identifying this span.")
    trace_id: str = Field(description="UUID4 of the parent trace.")
    parent_span_id: Optional[str] = Field(
        default=None,
        description="UUID4 of the parent span, or None for top-level spans.",
    )
    name: str = Field(description="Human-readable name for this span.")
    span_type: str = Field(
        description="Category of span. Recommended values: 'llm', 'tool', 'retrieval', 'chain', 'custom'.",
    )
    started_at: datetime = Field(description="UTC timestamp when the span started.")
    ended_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp when the span ended. None if still open.",
    )
    duration_ms: Optional[float] = Field(
        default=None,
        description="Elapsed time in milliseconds (derived from started_at/ended_at).",
    )

    # I/O
    input_text: Optional[str] = Field(default=None, description="Text input to this span.")
    output_text: Optional[str] = Field(default=None, description="Text output from this span.")

    # LLM-specific fields
    model: Optional[str] = Field(default=None, description="Model identifier (e.g., 'gpt-4o').")
    tokens_input: Optional[int] = Field(default=None, ge=0, description="Prompt token count.")
    tokens_output: Optional[int] = Field(default=None, ge=0, description="Completion token count.")
    cost_usd: Optional[float] = Field(
        default=None, ge=0, description="Estimated cost in USD based on the model's pricing."
    )

    # Status
    status: str = Field(
        default="ok",
        description="Span exit status. One of: 'ok', 'error'.",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Exception message when status='error'.",
    )
    error_type: Optional[str] = Field(
        default=None,
        description="Fully-qualified exception class name when status='error'.",
    )

    # Arbitrary metadata bag
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary key-value pairs attached to this span.",
    )

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: str) -> str:
        allowed = {"ok", "error"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}; got {v!r}")
        return v


# ---------------------------------------------------------------------------
# Trace data
# ---------------------------------------------------------------------------

class TraceData(BaseModel):
    """
    Wire-format model for a complete agent trace sent to the AgentOps backend.

    A trace represents one complete agent run (or any logical unit of work).
    It carries a list of child :class:`SpanData` objects collected during the run.
    """

    trace_id: str = Field(description="UUID4 string uniquely identifying this trace.")
    session_id: Optional[str] = Field(
        default=None,
        description="Caller-supplied session identifier for grouping related traces.",
    )
    agent_name: str = Field(description="Name of the agent that owns this trace.")

    started_at: datetime = Field(description="UTC timestamp when the trace started.")
    ended_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp when the trace ended. None if still open.",
    )
    duration_ms: Optional[float] = Field(
        default=None,
        description="Total elapsed time in milliseconds.",
    )

    status: str = Field(
        default="ok",
        description="Trace exit status. One of: 'ok', 'error'.",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Top-level exception message when status='error'.",
    )
    error_type: Optional[str] = Field(
        default=None,
        description="Top-level exception class name when status='error'.",
    )

    spans: List[SpanData] = Field(
        default_factory=list,
        description="All child spans captured during this trace.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary key-value metadata attached by the caller.",
    )

    # SDK bookkeeping — not sent if None
    sdk_version: Optional[str] = Field(
        default="0.1.0",
        description="Version of the agentops-sdk that produced this trace.",
    )

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: str) -> str:
        allowed = {"ok", "error"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}; got {v!r}")
        return v
