"""
app/models/project.py
=====================
Project model.

A Project is a logical container for API keys, traces, eval datasets,
and governance policies.  One Org can own many projects.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Project(Base):
    """Logical workspace scoped to a single Org."""

    __tablename__ = "projects"

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
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

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
    org: Mapped["Org"] = relationship("Org", back_populates="projects")  # type: ignore[name-defined]  # noqa: F821
    api_keys: Mapped[list["APIKey"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "APIKey", back_populates="project", cascade="all, delete-orphan"
    )
    traces: Mapped[list["Trace"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Trace", back_populates="project", cascade="all, delete-orphan"
    )
    eval_datasets: Mapped[list["EvalDataset"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "EvalDataset", back_populates="project", cascade="all, delete-orphan"
    )
    eval_runs: Mapped[list["EvalRun"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "EvalRun", back_populates="project", cascade="all, delete-orphan"
    )
    policies: Mapped[list["Policy"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Policy", back_populates="project", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "AuditLog", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name!r}>"
