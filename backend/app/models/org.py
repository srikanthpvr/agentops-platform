"""
app/models/org.py
=================
Organisation (tenant) model.

Each ``Org`` is an independent billing and access-control boundary.
Users belong to exactly one Org; Projects are scoped to an Org.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class OrgTier(str, enum.Enum):
    """Subscription tier that determines rate limits and feature access."""

    free = "free"
    pro = "pro"
    enterprise = "enterprise"


class Org(Base):
    """Top-level tenant that owns users, projects, and billing data."""

    __tablename__ = "orgs"

    # ------------------------------------------------------------------
    # Primary key – UUIDs prevent enumeration attacks
    # ------------------------------------------------------------------
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Org identity
    # ------------------------------------------------------------------
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Stripe customer ID; populated on first payment event
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )

    # ------------------------------------------------------------------
    # Billing tier & usage counters
    # ------------------------------------------------------------------
    tier: Mapped[OrgTier] = mapped_column(
        Enum(OrgTier, name="org_tier_enum"),
        nullable=False,
        default=OrgTier.free,
        server_default=OrgTier.free.value,
    )

    # Traces ingested in the current billing month (reset monthly by a cron)
    traces_this_month: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # Maximum traces allowed per month for the current tier
    tier_limit_traces: Mapped[int] = mapped_column(
        Integer, nullable=False, default=10_000, server_default="10000"
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
    # Relationships (back-populated from child models)
    # ------------------------------------------------------------------
    users: Mapped[list["User"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User", back_populates="org", cascade="all, delete-orphan"
    )
    projects: Mapped[list["Project"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Project", back_populates="org", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Org id={self.id} name={self.name!r} tier={self.tier}>"
