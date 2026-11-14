"""
app/api/v1/traces.py
====================
Trace ingestion and query endpoints.

Ingestion is authenticated via ``X-API-Key`` header (SDK/agent calls).
Query endpoints are authenticated via JWT (dashboard/user calls).
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_active_user, get_project_by_api_key
from app.models.project import Project
from app.models.span import Span, SpanType
from app.models.trace import Trace, TraceStatus
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.trace import SpanResponse, TraceCreate, TraceResponse, TraceUpdate

router = APIRouter(tags=["Traces"])


# ---------------------------------------------------------------------------
# Ingestion endpoint (API key auth)
# ---------------------------------------------------------------------------

@router.post(
    "/ingest/traces",
    response_model=TraceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a trace (and all its spans) from an SDK or agent.",
)
async def ingest_trace(
    payload: TraceCreate,
    project: Project = Depends(get_project_by_api_key),
    db: AsyncSession = Depends(get_db),
) -> TraceResponse:
    """Atomically write a Trace and all its child Spans in one transaction.

    After persisting, a Celery task is enqueued to recalculate aggregate
    cost/token metrics asynchronously (handles SDK-submitted spans where
    cost may be ``0.0`` and needs to be derived from model pricing).
    """
    # Determine trace UUID (allow caller to supply for idempotency)
    trace_id = payload.id or uuid.uuid4()

    # Build the Trace ORM object
    trace = Trace(
        id=trace_id,
        project_id=project.id,
        session_id=payload.session_id,
        agent_name=payload.agent_name,
        status=TraceStatus.running,
        total_tokens=0,
        total_cost_usd=0.0,
        metadata_=payload.metadata,
        started_at=payload.started_at,
    )
    db.add(trace)

    # Build all Span ORM objects
    for span_data in payload.spans:
        span = Span(
            id=span_data.id or uuid.uuid4(),
            trace_id=trace_id,
            parent_span_id=span_data.parent_span_id,
            name=span_data.name,
            span_type=SpanType(span_data.span_type)
            if span_data.span_type in SpanType.__members__
            else SpanType.custom,
            input_=span_data.input,
            output_=span_data.output,
            model=span_data.model,
            tokens_input=span_data.tokens_input,
            tokens_output=span_data.tokens_output,
            cost_usd=span_data.cost_usd,
            latency_ms=span_data.latency_ms,
            started_at=span_data.started_at,
            ended_at=span_data.ended_at,
            error=span_data.error,
            metadata_=span_data.metadata,
        )
        db.add(span)

    await db.commit()
    await db.refresh(trace)

    # Enqueue async cost recalculation (import inline to avoid circular deps)
    try:
        from app.workers.celery_app import recalculate_trace_cost  # noqa: PLC0415
        recalculate_trace_cost.delay(str(trace_id))
    except Exception:  # pragma: no cover – Celery may be unavailable in tests
        pass

    return TraceResponse(
        id=trace.id,
        project_id=trace.project_id,
        session_id=trace.session_id,
        agent_name=trace.agent_name,
        status=trace.status.value,
        duration_ms=trace.duration_ms,
        total_tokens=trace.total_tokens,
        total_cost_usd=trace.total_cost_usd,
        metadata_=trace.metadata_,
        started_at=trace.started_at,
        ended_at=trace.ended_at,
        created_at=trace.created_at,
        span_count=len(payload.spans),
    )


# ---------------------------------------------------------------------------
# JWT-authenticated query endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/projects/{project_id}/traces",
    response_model=PaginatedResponse[TraceResponse],
    summary="List traces for a project with optional filters.",
)
async def list_traces(
    project_id: uuid.UUID,
    # Filters
    status: str | None = Query(default=None),
    agent_name: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    # Pagination
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[TraceResponse]:
    """Return a paginated, filtered list of traces for the project."""
    # Validate project belongs to the user's org
    proj_result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.org_id == current_user.org_id,
        )
    )
    if proj_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    # Build filter conditions
    conditions = [Trace.project_id == project_id]
    if status:
        conditions.append(Trace.status == status)
    if agent_name:
        conditions.append(Trace.agent_name == agent_name)
    if session_id:
        conditions.append(Trace.session_id == session_id)
    if date_from:
        conditions.append(Trace.started_at >= date_from)
    if date_to:
        conditions.append(Trace.started_at <= date_to)

    where_clause = and_(*conditions)

    total_result = await db.execute(
        select(func.count()).select_from(Trace).where(where_clause)
    )
    total: int = total_result.scalar_one()

    offset = (page - 1) * page_size
    rows_result = await db.execute(
        select(Trace)
        .where(where_clause)
        .order_by(Trace.started_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    traces = rows_result.scalars().all()

    items = [
        TraceResponse(
            id=t.id,
            project_id=t.project_id,
            session_id=t.session_id,
            agent_name=t.agent_name,
            status=t.status.value,
            duration_ms=t.duration_ms,
            total_tokens=t.total_tokens,
            total_cost_usd=t.total_cost_usd,
            metadata_=t.metadata_,
            started_at=t.started_at,
            ended_at=t.ended_at,
            created_at=t.created_at,
            span_count=0,  # skipped on list for performance
        )
        for t in traces
    ]

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, -(-total // page_size)),
    )


@router.get(
    "/projects/{project_id}/traces/{trace_id}",
    response_model=TraceResponse,
    summary="Get a single trace with all its spans.",
)
async def get_trace(
    project_id: uuid.UUID,
    trace_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TraceResponse:
    """Return a trace with all child spans eagerly loaded."""
    result = await db.execute(
        select(Trace)
        .options(selectinload(Trace.spans))
        .where(
            Trace.id == trace_id,
            Trace.project_id == project_id,
        )
    )
    trace = result.scalar_one_or_none()
    if trace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trace {trace_id} not found.",
        )

    # Verify org ownership via project
    proj_result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.org_id == current_user.org_id,
        )
    )
    if proj_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    span_responses = [
        SpanResponse(
            id=s.id,
            trace_id=s.trace_id,
            parent_span_id=s.parent_span_id,
            name=s.name,
            span_type=s.span_type.value,
            input_=s.input_,
            output_=s.output_,
            model=s.model,
            tokens_input=s.tokens_input,
            tokens_output=s.tokens_output,
            cost_usd=s.cost_usd,
            latency_ms=s.latency_ms,
            started_at=s.started_at,
            ended_at=s.ended_at,
            error=s.error,
            metadata_=s.metadata_,
            created_at=s.created_at,
        )
        for s in trace.spans
    ]

    return TraceResponse(
        id=trace.id,
        project_id=trace.project_id,
        session_id=trace.session_id,
        agent_name=trace.agent_name,
        status=trace.status.value,
        duration_ms=trace.duration_ms,
        total_tokens=trace.total_tokens,
        total_cost_usd=trace.total_cost_usd,
        metadata_=trace.metadata_,
        started_at=trace.started_at,
        ended_at=trace.ended_at,
        created_at=trace.created_at,
        span_count=len(trace.spans),
        spans=span_responses,
    )


@router.patch(
    "/projects/{project_id}/traces/{trace_id}",
    response_model=TraceResponse,
    summary="Update a trace's status or end time.",
)
async def update_trace(
    project_id: uuid.UUID,
    trace_id: uuid.UUID,
    payload: TraceUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TraceResponse:
    """Partial update of a Trace (e.g. mark as completed)."""
    result = await db.execute(
        select(Trace).where(
            Trace.id == trace_id,
            Trace.project_id == project_id,
        )
    )
    trace = result.scalar_one_or_none()
    if trace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trace {trace_id} not found.",
        )

    # Verify org ownership
    proj_result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.org_id == current_user.org_id,
        )
    )
    if proj_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    if payload.status is not None:
        try:
            trace.status = TraceStatus(payload.status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status: {payload.status!r}",
            )
    if payload.ended_at is not None:
        trace.ended_at = payload.ended_at
        if trace.started_at:
            diff = payload.ended_at - trace.started_at
            trace.duration_ms = diff.total_seconds() * 1000
    if payload.total_tokens is not None:
        trace.total_tokens = payload.total_tokens
    if payload.total_cost_usd is not None:
        trace.total_cost_usd = payload.total_cost_usd

    await db.commit()
    await db.refresh(trace)

    return TraceResponse(
        id=trace.id,
        project_id=trace.project_id,
        session_id=trace.session_id,
        agent_name=trace.agent_name,
        status=trace.status.value,
        duration_ms=trace.duration_ms,
        total_tokens=trace.total_tokens,
        total_cost_usd=trace.total_cost_usd,
        metadata_=trace.metadata_,
        started_at=trace.started_at,
        ended_at=trace.ended_at,
        created_at=trace.created_at,
        span_count=0,
    )


@router.get(
    "/projects/{project_id}/stats",
    summary="Aggregate stats for the last 30 days.",
)
async def get_project_stats(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return daily aggregate stats grouped by calendar day for 30 days.

    Fields per day:
    - ``date`` – ISO date string
    - ``total_traces`` – count of traces started on that day
    - ``total_tokens`` – sum of total_tokens
    - ``total_cost_usd`` – sum of total_cost_usd
    - ``avg_latency_ms`` – average duration_ms (excludes nulls)
    - ``error_count`` – traces with status=error
    """
    # Verify project membership
    proj_result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.org_id == current_user.org_id,
        )
    )
    if proj_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    from datetime import timedelta
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    # Cross-database compatible aggregation (PostgreSQL & SQLite)
    summary_stmt = select(
        func.count(Trace.id).label("total_traces"),
        func.sum(Trace.total_tokens).label("total_tokens"),
        func.sum(Trace.total_cost_usd).label("total_cost_usd"),
        func.avg(Trace.duration_ms).label("avg_latency_ms"),
    ).where(
        Trace.project_id == project_id,
        Trace.started_at >= thirty_days_ago,
    )
    summary_res = await db.execute(summary_stmt)
    summary = summary_res.one()

    # Query recent traces for daily chart formatting
    recent_traces_res = await db.execute(
        select(Trace.started_at, Trace.total_tokens, Trace.total_cost_usd, Trace.status)
        .where(Trace.project_id == project_id, Trace.started_at >= thirty_days_ago)
        .order_by(Trace.started_at.asc())
    )
    all_traces = recent_traces_res.all()

    daily_map = {}
    error_count = 0
    for t in all_traces:
        if t.status == TraceStatus.error:
            error_count += 1
        d_str = t.started_at.strftime("%Y-%m-%d") if t.started_at else "unknown"
        if d_str not in daily_map:
            daily_map[d_str] = {"date": d_str, "traces": 0, "cost": 0.0, "tokens": 0}
        daily_map[d_str]["traces"] += 1
        daily_map[d_str]["cost"] = round(daily_map[d_str]["cost"] + (t.total_cost_usd or 0.0), 6)
        daily_map[d_str]["tokens"] += t.total_tokens or 0

    total_traces = summary.total_traces or 0
    return {
        "project_id": str(project_id),
        "total_traces": total_traces,
        "total_tokens": int(summary.total_tokens or 0),
        "total_cost_usd": float(summary.total_cost_usd or 0.0),
        "avg_latency_ms": float(summary.avg_latency_ms or 0.0),
        "error_rate": round(error_count / total_traces, 4) if total_traces > 0 else 0.0,
        "daily": list(daily_map.values()),
        "days": list(daily_map.values()),
    }
