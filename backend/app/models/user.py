"""
app/models/user.py
==================
User model.

A User belongs to one Org and has a role (owner / admin / member).
Passwords are stored as bcrypt hashes — never in plain text.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class UserRole(str, enum.Enum):
    """Permission level within an organisation."""

    owner = "owner"    # Full control, including billing and org deletion
    admin = "admin"    # Manage projects, keys, policies; cannot delete org
    member = "member"  # Read / write traces; cannot change settings


class User(Base):
    """Authenticated human user of the platform."""

    __tablename__ = "users"

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
    # Org membership
    # ------------------------------------------------------------------
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Identity & credentials
    # ------------------------------------------------------------------
    email: Mapped[str] = mapped_column(
        String(320),  # RFC 5321 max email length
        nullable=False,
        unique=True,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # ------------------------------------------------------------------
    # Authorisation
    # ------------------------------------------------------------------
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum"),
        nullable=False,
        default=UserRole.member,
        server_default=UserRole.member.value,
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
    org: Mapped["Org"] = relationship("Org", back_populates="users")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role}>"
