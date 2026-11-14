"""
app/models/trace.py
===================
Trace model.

A Trace represents a single end-to-end agent execution.  It aggregates
all Spans generated during that execution and rolls up cost / token
metrics for fast dashboard queries.

The composite index on ``(project_id, started_at)`` supports time-range
queries filtered by project — the dominant access pattern for the UI.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class TraceStatus(str, enum.Enum):
    """Lifecycle status of an agent trace."""

    running = "running"
    success = "success"
    error = "error"


class Trace(Base):
    """Single agent execution recorded as an observable trace."""

    __tablename__ = "traces"

    # Composite index for time-range dashboard queries
    __table_args__ = (
        Index("ix_traces_project_started", "project_id", "started_at"),
    )

    # ------------------------------------------------------------------
    # Primary key
    # ------------------------------------------------------------------
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Ownership
    # ------------------------------------------------------------------
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Trace identity
    # ------------------------------------------------------------------
    # Optional grouping key – callers may group multiple traces under one session
    session_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    agent_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # ------------------------------------------------------------------
    # Status & timing
    # ------------------------------------------------------------------
    status: Mapped[TraceStatus] = mapped_column(
        Enum(TraceStatus, name="trace_status_enum"),
        nullable=False,
        default=TraceStatus.running,
        server_default=TraceStatus.running.value,
    )
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ------------------------------------------------------------------
    # Aggregated metrics (denormalised from child Spans for fast reads)
    # ------------------------------------------------------------------
    total_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    total_cost_usd: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, server_default="0"
    )

    # ------------------------------------------------------------------
    # Arbitrary caller-supplied metadata (e.g. environment tags)
    # ------------------------------------------------------------------
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSON, nullable=True
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    project: Mapped["Project"] = relationship("Project", back_populates="traces")  # type: ignore[name-defined]  # noqa: F821
    spans: Mapped[list["Span"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Span", back_populates="trace", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Trace id={self.id} agent={self.agent_name!r} status={self.status}>"
        )
