"""
app/models/audit_log.py
=======================
Audit Log model.

Every policy violation generates an immutable AuditLog record.
Audit logs are append-only; they are never updated or deleted.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ViolationSeverity(str, enum.Enum):
    """Risk level assigned to a policy violation."""

    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AuditLog(Base):
    """Immutable record of a policy violation event."""

    __tablename__ = "audit_logs"

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
    # Context references
    # ------------------------------------------------------------------
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # The trace that triggered the violation (nullable if not trace-related)
    trace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    # Which policy fired (nullable if the violation predates policy records)
    policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # Violation details
    # ------------------------------------------------------------------
    violation_type: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    severity: Mapped[ViolationSeverity] = mapped_column(
        Enum(ViolationSeverity, name="violation_severity_enum"),
        nullable=False,
        default=ViolationSeverity.medium,
        server_default=ViolationSeverity.medium.value,
        index=True,
    )

    # Arbitrary evidence payload (truncated PII, matched patterns, etc.)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    # ------------------------------------------------------------------
    # Timestamp (audit logs are immutable — no updated_at)
    # ------------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    project: Mapped["Project"] = relationship("Project", back_populates="audit_logs")  # type: ignore[name-defined]  # noqa: F821
    policy: Mapped["Policy | None"] = relationship("Policy", back_populates="audit_logs")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} type={self.violation_type!r} "
            f"severity={self.severity}>"
        )
