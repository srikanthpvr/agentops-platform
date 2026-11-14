"""
app/models/eval_dataset.py
==========================
Evaluation Dataset model.

An EvalDataset is a versioned collection of input/expected-output rows
used to benchmark LLM agents against a consistent test bed.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class EvalDataset(Base):
    """Named, versioned dataset of evaluation examples."""

    __tablename__ = "eval_datasets"

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
    # Dataset metadata
    # ------------------------------------------------------------------
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # JSON Schema that describes the structure of each row
    schema_: Mapped[dict | None] = mapped_column("schema", JSON, nullable=True)

    # Cached count of rows; updated when rows are added/removed
    row_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    project: Mapped["Project"] = relationship("Project", back_populates="eval_datasets")  # type: ignore[name-defined]  # noqa: F821
    eval_runs: Mapped[list["EvalRun"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "EvalRun", back_populates="dataset"
    )

    def __repr__(self) -> str:
        return f"<EvalDataset id={self.id} name={self.name!r} rows={self.row_count}>"
