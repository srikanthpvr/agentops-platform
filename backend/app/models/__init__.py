"""
app/models/__init__.py
======================
Re-export all ORM models so that:

1. ``import app.models`` guarantees every model class is registered with
   SQLAlchemy's metadata before ``Base.metadata.create_all()`` is called.
2. Alembic autogenerate can discover all table definitions.
3. Application code can do ``from app.models import User`` without knowing
   which sub-module each model lives in.
"""

from app.models.api_key import APIKey  # noqa: F401
from app.models.audit_log import AuditLog, ViolationSeverity  # noqa: F401
from app.models.eval_dataset import EvalDataset  # noqa: F401
from app.models.eval_run import EvalRun, EvalRunStatus  # noqa: F401
from app.models.org import Org, OrgTier  # noqa: F401
from app.models.policy import Policy, PolicyAction  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.span import Span, SpanType  # noqa: F401
from app.models.trace import Trace, TraceStatus  # noqa: F401
from app.models.user import User, UserRole  # noqa: F401

__all__ = [
    "APIKey",
    "AuditLog",
    "ViolationSeverity",
    "EvalDataset",
    "EvalRun",
    "EvalRunStatus",
    "Org",
    "OrgTier",
    "Policy",
    "PolicyAction",
    "Project",
    "Span",
    "SpanType",
    "Trace",
    "TraceStatus",
    "User",
    "UserRole",
]
