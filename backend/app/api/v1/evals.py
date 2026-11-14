"""
app/api/v1/evals.py
===================
Evaluation dataset and run management endpoints.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.eval_dataset import EvalDataset
from app.models.eval_run import EvalRun, EvalRunStatus
from app.models.project import Project
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.eval import (
    EvalDatasetCreate,
    EvalDatasetResponse,
    EvalRunCreate,
    EvalRunResponse,
)

router = APIRouter(tags=["Evaluations"])


# ---------------------------------------------------------------------------
# Helper: verify project belongs to the current user's org
# ---------------------------------------------------------------------------

async def _assert_project(
    project_id: uuid.UUID,
    user: User,
    db: AsyncSession,
) -> Project:
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.org_id == user.org_id,
        )
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


# ---------------------------------------------------------------------------
# EvalDataset endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/projects/{project_id}/eval-datasets",
    response_model=PaginatedResponse[EvalDatasetResponse],
    summary="List evaluation datasets for a project.",
)
async def list_eval_datasets(
    project_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[EvalDatasetResponse]:
    await _assert_project(project_id, current_user, db)

    total_result = await db.execute(
        select(func.count())
        .select_from(EvalDataset)
        .where(EvalDataset.project_id == project_id)
    )
    total: int = total_result.scalar_one()

    offset = (page - 1) * page_size
    rows_result = await db.execute(
        select(EvalDataset)
        .where(EvalDataset.project_id == project_id)
        .order_by(EvalDataset.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    datasets = rows_result.scalars().all()

    return PaginatedResponse(
        items=[
            EvalDatasetResponse(
                id=d.id,
                project_id=d.project_id,
                name=d.name,
                description=d.description,
                schema_=d.schema_,
                row_count=d.row_count,
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
            for d in datasets
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, -(-total // page_size)),
    )


@router.post(
    "/projects/{project_id}/eval-datasets",
    response_model=EvalDatasetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new evaluation dataset.",
)
async def create_eval_dataset(
    project_id: uuid.UUID,
    payload: EvalDatasetCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> EvalDatasetResponse:
    await _assert_project(project_id, current_user, db)

    dataset = EvalDataset(
        project_id=project_id,
        name=payload.name,
        description=payload.description,
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)

    return EvalDatasetResponse(
        id=dataset.id,
        project_id=dataset.project_id,
        name=dataset.name,
        description=dataset.description,
        schema_=dataset.schema_,
        row_count=dataset.row_count,
        created_at=dataset.created_at,
        updated_at=dataset.updated_at,
    )


# ---------------------------------------------------------------------------
# EvalRun endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/projects/{project_id}/eval-runs",
    response_model=PaginatedResponse[EvalRunResponse],
    summary="List evaluation runs for a project.",
)
async def list_eval_runs(
    project_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[EvalRunResponse]:
    await _assert_project(project_id, current_user, db)

    total_result = await db.execute(
        select(func.count())
        .select_from(EvalRun)
        .where(EvalRun.project_id == project_id)
    )
    total: int = total_result.scalar_one()

    offset = (page - 1) * page_size
    rows_result = await db.execute(
        select(EvalRun)
        .where(EvalRun.project_id == project_id)
        .order_by(EvalRun.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    runs = rows_result.scalars().all()

    return PaginatedResponse(
        items=[
            EvalRunResponse(
                id=r.id,
                project_id=r.project_id,
                dataset_id=r.dataset_id,
                name=r.name,
                model_config_=r.model_config_,
                judge_config=r.judge_config,
                status=r.status.value,
                avg_score=r.avg_score,
                started_at=r.started_at,
                finished_at=r.finished_at,
                created_at=r.created_at,
            )
            for r in runs
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, -(-total // page_size)),
    )


@router.post(
    "/projects/{project_id}/eval-runs",
    response_model=EvalRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and enqueue a new evaluation run.",
)
async def create_eval_run(
    project_id: uuid.UUID,
    payload: EvalRunCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> EvalRunResponse:
    """Create an EvalRun record and immediately enqueue a Celery task."""
    await _assert_project(project_id, current_user, db)

    # Verify dataset belongs to the same project
    dataset_result = await db.execute(
        select(EvalDataset).where(
            EvalDataset.id == payload.dataset_id,
            EvalDataset.project_id == project_id,
        )
    )
    if dataset_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"EvalDataset {payload.dataset_id} not found in this project.",
        )

    run = EvalRun(
        project_id=project_id,
        dataset_id=payload.dataset_id,
        name=payload.name,
        model_config_=payload.model_config_,
        judge_config=payload.judge_config,
        status=EvalRunStatus.pending,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Enqueue the async evaluation task
    try:
        from app.workers.celery_app import run_eval  # noqa: PLC0415
        run_eval.delay(str(run.id))
    except Exception:  # pragma: no cover
        pass

    return EvalRunResponse(
        id=run.id,
        project_id=run.project_id,
        dataset_id=run.dataset_id,
        name=run.name,
        model_config_=run.model_config_,
        judge_config=run.judge_config,
        status=run.status.value,
        avg_score=run.avg_score,
        started_at=run.started_at,
        finished_at=run.finished_at,
        created_at=run.created_at,
    )
