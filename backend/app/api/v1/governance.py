"""
app/api/v1/governance.py
========================
Governance policy management and audit log query endpoints.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.audit_log import AuditLog
from app.models.policy import Policy, PolicyAction
from app.models.project import Project
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.governance import (
    AuditLogResponse,
    PolicyCreate,
    PolicyResponse,
    PolicyUpdate,
)

router = APIRouter(tags=["Governance"])


# ---------------------------------------------------------------------------
# Helper
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
# Policy CRUD
# ---------------------------------------------------------------------------

@router.get(
    "/projects/{project_id}/policies",
    response_model=list[PolicyResponse],
    summary="List all governance policies for a project.",
)
async def list_policies(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[PolicyResponse]:
    await _assert_project(project_id, current_user, db)

    result = await db.execute(
        select(Policy)
        .where(Policy.project_id == project_id)
        .order_by(Policy.created_at.desc())
    )
    policies = result.scalars().all()
    return [
        PolicyResponse(
            id=p.id,
            project_id=p.project_id,
            name=p.name,
            description=p.description,
            rules=p.rules,
            action=p.action.value,
            is_enabled=p.is_enabled,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in policies
    ]


@router.post(
    "/projects/{project_id}/policies",
    response_model=PolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new governance policy.",
)
async def create_policy(
    project_id: uuid.UUID,
    payload: PolicyCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PolicyResponse:
    await _assert_project(project_id, current_user, db)

    try:
        action = PolicyAction(payload.action)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid action: {payload.action!r}. Must be log|block|alert.",
        )

    policy = Policy(
        project_id=project_id,
        name=payload.name,
        description=payload.description,
        rules=payload.rules,
        action=action,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)

    return PolicyResponse(
        id=policy.id,
        project_id=policy.project_id,
        name=policy.name,
        description=policy.description,
        rules=policy.rules,
        action=policy.action.value,
        is_enabled=policy.is_enabled,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


@router.patch(
    "/projects/{project_id}/policies/{policy_id}",
    response_model=PolicyResponse,
    summary="Update a governance policy.",
)
async def update_policy(
    project_id: uuid.UUID,
    policy_id: uuid.UUID,
    payload: PolicyUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PolicyResponse:
    await _assert_project(project_id, current_user, db)

    result = await db.execute(
        select(Policy).where(
            Policy.id == policy_id,
            Policy.project_id == project_id,
        )
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found.")

    if payload.name is not None:
        policy.name = payload.name
    if payload.rules is not None:
        policy.rules = payload.rules
    if payload.action is not None:
        try:
            policy.action = PolicyAction(payload.action)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid action: {payload.action!r}.",
            )
    if payload.is_enabled is not None:
        policy.is_enabled = payload.is_enabled

    await db.commit()
    await db.refresh(policy)

    return PolicyResponse(
        id=policy.id,
        project_id=policy.project_id,
        name=policy.name,
        description=policy.description,
        rules=policy.rules,
        action=policy.action.value,
        is_enabled=policy.is_enabled,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


@router.delete(
    "/projects/{project_id}/policies/{policy_id}",
    response_model=MessageResponse,
    summary="Delete a governance policy.",
)
async def delete_policy(
    project_id: uuid.UUID,
    policy_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await _assert_project(project_id, current_user, db)

    result = await db.execute(
        select(Policy).where(
            Policy.id == policy_id,
            Policy.project_id == project_id,
        )
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found.")

    await db.delete(policy)
    await db.commit()
    return MessageResponse(message=f"Policy {policy_id} deleted.")


# ---------------------------------------------------------------------------
# Audit Log queries
# ---------------------------------------------------------------------------

@router.get(
    "/projects/{project_id}/audit-logs",
    response_model=PaginatedResponse[AuditLogResponse],
    summary="List audit logs (policy violation events) for a project.",
)
async def list_audit_logs(
    project_id: uuid.UUID,
    # Optional filters
    severity: str | None = Query(default=None),
    violation_type: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    # Pagination
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[AuditLogResponse]:
    """Return a filterable, paginated list of audit log entries."""
    await _assert_project(project_id, current_user, db)

    conditions = [AuditLog.project_id == project_id]
    if severity:
        conditions.append(AuditLog.severity == severity)
    if violation_type:
        conditions.append(AuditLog.violation_type == violation_type)
    if date_from:
        from datetime import datetime  # noqa: PLC0415
        conditions.append(
            AuditLog.created_at >= datetime.fromisoformat(date_from)
        )
    if date_to:
        from datetime import datetime  # noqa: PLC0415
        conditions.append(
            AuditLog.created_at <= datetime.fromisoformat(date_to)
        )

    where_clause = and_(*conditions)

    total_result = await db.execute(
        select(func.count()).select_from(AuditLog).where(where_clause)
    )
    total: int = total_result.scalar_one()

    offset = (page - 1) * page_size
    rows_result = await db.execute(
        select(AuditLog)
        .where(where_clause)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    logs = rows_result.scalars().all()

    return PaginatedResponse(
        items=[
            AuditLogResponse(
                id=log.id,
                project_id=log.project_id,
                trace_id=log.trace_id,
                policy_id=log.policy_id,
                violation_type=log.violation_type,
                severity=log.severity.value,
                payload=log.payload,
                created_at=log.created_at,
            )
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, -(-total // page_size)),
    )
