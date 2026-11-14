"""
app/api/v1/projects.py
======================
Project management and API key CRUD endpoints.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.security import generate_api_key
from app.models.api_key import APIKey
from app.models.project import Project
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.project import (
    APIKeyCreate,
    APIKeyCreatedResponse,
    APIKeyResponse,
    ProjectCreate,
    ProjectResponse,
)

router = APIRouter(prefix="/projects", tags=["Projects"])


# ---------------------------------------------------------------------------
# Helper: assert the project belongs to the current user's org
# ---------------------------------------------------------------------------

async def _get_project_for_user(
    project_id: uuid.UUID,
    user: User,
    db: AsyncSession,
) -> Project:
    """Load a project, verifying it belongs to the user's organisation.

    Raises:
        HTTPException 404: If the project does not exist or is inaccessible.
    """
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.org_id == user.org_id,
        )
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found.",
        )
    return project


# ---------------------------------------------------------------------------
# Project CRUD
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=PaginatedResponse[ProjectResponse],
    summary="List all projects for the authenticated user's organisation.",
)
async def list_projects(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ProjectResponse]:
    """Return a paginated list of projects owned by the current org."""
    # Total count
    count_result = await db.execute(
        select(func.count()).select_from(Project).where(
            Project.org_id == current_user.org_id
        )
    )
    total: int = count_result.scalar_one()

    # Paged rows
    offset = (page - 1) * page_size
    rows_result = await db.execute(
        select(Project)
        .where(Project.org_id == current_user.org_id)
        .order_by(Project.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    projects = rows_result.scalars().all()

    return PaginatedResponse(
        items=[ProjectResponse.model_validate(p) for p in projects],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, -(-total // page_size)),  # ceiling division
    )


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project within the authenticated user's organisation.",
)
async def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Create and return a new :class:`Project`."""
    project = Project(
        org_id=current_user.org_id,
        name=payload.name,
        description=payload.description,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return ProjectResponse.model_validate(project)


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Retrieve a single project by ID.",
)
async def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Fetch a project, ensuring it belongs to the caller's org."""
    project = await _get_project_for_user(project_id, current_user, db)
    return ProjectResponse.model_validate(project)


@router.delete(
    "/{project_id}",
    response_model=MessageResponse,
    summary="Delete a project and all its resources.",
)
async def delete_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Permanently delete a project (cascade deletes all child records)."""
    project = await _get_project_for_user(project_id, current_user, db)
    await db.delete(project)
    await db.commit()
    return MessageResponse(message=f"Project {project_id} deleted.")


# ---------------------------------------------------------------------------
# API Key management
# ---------------------------------------------------------------------------

@router.post(
    "/{project_id}/api-keys",
    response_model=APIKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key for a project (full key shown once).",
)
async def create_api_key(
    project_id: uuid.UUID,
    payload: APIKeyCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> APIKeyCreatedResponse:
    """Generate a new API key and return it **once** in the response.

    The ``full_key`` field is irrecoverable after this response — only
    the prefix and hash are stored.
    """
    project = await _get_project_for_user(project_id, current_user, db)
    full_key, prefix, hashed = generate_api_key()

    api_key = APIKey(
        project_id=project.id,
        name=payload.name,
        key_prefix=prefix,
        key_hash=hashed,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return APIKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        full_key=full_key,
    )


@router.get(
    "/{project_id}/api-keys",
    response_model=list[APIKeyResponse],
    summary="List all API keys for a project (full key never returned).",
)
async def list_api_keys(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[APIKeyResponse]:
    """Return all API keys belonging to the project."""
    await _get_project_for_user(project_id, current_user, db)

    result = await db.execute(
        select(APIKey)
        .where(APIKey.project_id == project_id)
        .order_by(APIKey.created_at.desc())
    )
    keys = result.scalars().all()
    return [APIKeyResponse.model_validate(k) for k in keys]


@router.delete(
    "/{project_id}/api-keys/{key_id}",
    response_model=MessageResponse,
    summary="Revoke (soft-delete) an API key.",
)
async def revoke_api_key(
    project_id: uuid.UUID,
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Mark the API key as inactive.  Revoked keys cannot be reactivated."""
    await _get_project_for_user(project_id, current_user, db)

    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.project_id == project_id,
        )
    )
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found.",
        )

    api_key.is_active = False
    await db.commit()
    return MessageResponse(message=f"API key {key_id} revoked.")
