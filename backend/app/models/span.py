"""
app/models/span.py
==================
Span model.

A Span represents a single step (LLM call, tool use, retrieval, etc.)
within a parent Trace.  Spans may be nested via ``parent_span_id`` to
represent call hierarchies (e.g. an agent that calls a chain that calls
an LLM).
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class SpanType(str, enum.Enum):
    """Semantic category of work performed in a span."""

    llm = "llm"
    tool = "tool"
    chain = "chain"
    agent = "agent"
    retrieval = "retrieval"
    custom = "custom"


class Span(Base):
    """Atomic unit of work within a Trace."""

    __tablename__ = "spans"

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
    # Hierarchy
    # ------------------------------------------------------------------
    trace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("traces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Self-referential FK allows nesting spans into trees
    parent_span_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("spans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # Span identity & type
    # ------------------------------------------------------------------
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    span_type: Mapped[SpanType] = mapped_column(
        Enum(SpanType, name="span_type_enum"),
        nullable=False,
        default=SpanType.custom,
        server_default=SpanType.custom.value,
    )

    # ------------------------------------------------------------------
    # I/O (stored as Text to allow large payloads; consider S3 for >1 MB)
    # ------------------------------------------------------------------
    input_: Mapped[str | None] = mapped_column("input", Text, nullable=True)
    output_: Mapped[str | None] = mapped_column("output", Text, nullable=True)

    # ------------------------------------------------------------------
    # LLM metrics
    # ------------------------------------------------------------------
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tokens_input: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    tokens_output: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    cost_usd: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, server_default="0"
    )

    # ------------------------------------------------------------------
    # Timing
    # ------------------------------------------------------------------
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ------------------------------------------------------------------
    # Error & metadata
    # ------------------------------------------------------------------
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    trace: Mapped["Trace"] = relationship("Trace", back_populates="spans")  # type: ignore[name-defined]  # noqa: F821
    # Child spans (for tree traversal)
    children: Mapped[list["Span"]] = relationship(
        "Span",
        back_populates="parent",
        cascade="all",
        foreign_keys=[parent_span_id],
    )
    parent: Mapped["Span | None"] = relationship(
        "Span",
        back_populates="children",
        remote_side=[id],
        foreign_keys=[parent_span_id],
    )

    def __repr__(self) -> str:
        return f"<Span id={self.id} name={self.name!r} type={self.span_type}>"
