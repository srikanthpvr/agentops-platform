"""
app/workers/celery_app.py
=========================
Celery application instance and background tasks for async processing.
"""

import asyncio
from datetime import datetime, timezone
import uuid

from celery import Celery
from sqlalchemy import select, update

from app.core.config import settings

celery_app = Celery(
    "agentops_workers",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)


@celery_app.task(name="recalculate_trace_cost", bind=True, max_retries=3)
def recalculate_trace_cost(self, trace_id: str):
    """Celery task to aggregate span tokens/costs and update the parent trace."""
    from app.core.database import AsyncSessionLocal
    from app.models.span import Span
    from app.models.trace import Trace

    async def _async_recalc():
        async with AsyncSessionLocal() as db:
            trace_uuid = uuid.UUID(trace_id)
            spans_res = await db.execute(select(Span).where(Span.trace_id == trace_uuid))
            spans = spans_res.scalars().all()

            total_tokens = sum(s.tokens_input + s.tokens_output for s in spans)
            total_cost = sum(s.cost_usd for s in spans)

            await db.execute(
                update(Trace)
                .where(Trace.id == trace_uuid)
                .values(
                    total_tokens=total_tokens,
                    total_cost_usd=round(total_cost, 6),
                )
            )
            await db.commit()

    try:
        asyncio.run(_async_recalc())
        return {"status": "success", "trace_id": trace_id}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(name="run_eval", bind=True)
def run_eval(self, eval_run_id: str):
    """Background task to simulate or execute model evaluations."""
    from app.core.database import AsyncSessionLocal
    from app.models.eval_run import EvalRun, EvalRunStatus

    async def _async_eval():
        async with AsyncSessionLocal() as db:
            run_uuid = uuid.UUID(eval_run_id)
            res = await db.execute(select(EvalRun).where(EvalRun.id == run_uuid))
            eval_run = res.scalar_one_or_none()
            if not eval_run:
                return

            eval_run.status = EvalRunStatus.RUNNING
            eval_run.started_at = datetime.now(timezone.utc)
            await db.commit()

            # Simulated evaluation scoring calculation
            await asyncio.sleep(2)

            eval_run.status = EvalRunStatus.COMPLETED
            eval_run.avg_score = 0.885
            eval_run.finished_at = datetime.now(timezone.utc)
            await db.commit()

    asyncio.run(_async_eval())
    return {"status": "completed", "eval_run_id": eval_run_id}
