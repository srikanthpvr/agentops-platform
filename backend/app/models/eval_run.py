"""
app/models/eval_run.py
======================
Evaluation Run model.

An EvalRun executes a configured LLM judge over an EvalDataset and
records aggregate scores.  Runs are executed asynchronously by the
Celery worker.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class EvalRunStatus(str, enum.Enum):
    """Lifecycle status of an evaluation run."""

    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class EvalRun(Base):
    """Single execution of a judge model over an EvalDataset."""

    __tablename__ = "eval_runs"

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
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("eval_datasets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # JSON blob with model name, temperature, system prompt, etc.
    model_config_: Mapped[dict] = mapped_column("model_config", JSON, nullable=False)
    # Optional judge-model configuration (can differ from the agent model)
    judge_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------
    status: Mapped[EvalRunStatus] = mapped_column(
        Enum(EvalRunStatus, name="eval_run_status_enum"),
        nullable=False,
        default=EvalRunStatus.pending,
        server_default=EvalRunStatus.pending.value,
    )
    avg_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ------------------------------------------------------------------
    # Timing
    # ------------------------------------------------------------------
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
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
    project: Mapped["Project"] = relationship("Project", back_populates="eval_runs")  # type: ignore[name-defined]  # noqa: F821
    dataset: Mapped["EvalDataset"] = relationship("EvalDataset", back_populates="eval_runs")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<EvalRun id={self.id} name={self.name!r} status={self.status}>"
