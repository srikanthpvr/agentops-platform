"""
app/models/policy.py
====================
Governance Policy model.

A Policy defines a set of rules applied to agent traces (e.g. PII
detection, prompt injection blocking, cost caps).  Policies are
evaluated synchronously or asynchronously depending on the action.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class PolicyAction(str, enum.Enum):
    """What the platform does when a policy rule is triggered."""

    log = "log"      # Record the violation but allow the trace through
    block = "block"  # Reject the request with a 403 response
    alert = "alert"  # Send a webhook / notification and continue


class Policy(Base):
    """Governance rule applied to traces within a Project."""

    __tablename__ = "policies"

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
    # Policy definition
    # ------------------------------------------------------------------
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # JSON structure defining one or more rule conditions
    # Example: {"type": "pii_detection", "entities": ["EMAIL", "PHONE_NUMBER"]}
    rules: Mapped[dict] = mapped_column(JSON, nullable=False)

    action: Mapped[PolicyAction] = mapped_column(
        Enum(PolicyAction, name="policy_action_enum"),
        nullable=False,
        default=PolicyAction.log,
        server_default=PolicyAction.log.value,
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
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
    project: Mapped["Project"] = relationship("Project", back_populates="policies")  # type: ignore[name-defined]  # noqa: F821
    audit_logs: Mapped[list["AuditLog"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "AuditLog", back_populates="policy"
    )

    def __repr__(self) -> str:
        return f"<Policy id={self.id} name={self.name!r} action={self.action}>"
