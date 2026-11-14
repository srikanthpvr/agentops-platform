"""
app/models/api_key.py
=====================
API Key model.

Each APIKey is scoped to a Project.  Only the key *hash* is stored;
the full key is shown to the user exactly once at creation time and is
irrecoverable afterwards.  Lookups are performed by the ``key_prefix``
index followed by constant-time hash verification.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class APIKey(Base):
    """Programmatic access credential scoped to a Project."""

    __tablename__ = "api_keys"

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
    # Key material (never store the full plain-text key)
    # ------------------------------------------------------------------
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Human-readable label for this key"
    )
    # Indexed prefix used to narrow database lookups without full table scan
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    # PBKDF2-sha256 hash of the full API key
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # ------------------------------------------------------------------
    # Usage tracking
    # ------------------------------------------------------------------
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
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

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    project: Mapped["Project"] = relationship("Project", back_populates="api_keys")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<APIKey id={self.id} prefix={self.key_prefix!r} active={self.is_active}>"
