"""
app/core/deps.py
================
Reusable FastAPI dependency functions.

Conventions:
* Every dependency raises a typed HTTPException so OpenAPI documents
  the possible error responses.
* ``require_role`` is a factory (closure) pattern — it returns a
  dependency function, not a dependency result, so it can be used as
  ``Depends(require_role("owner", "admin"))``.
"""

import uuid
from datetime import datetime, timezone
from typing import Callable

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token, verify_api_key
from app.models.api_key import APIKey
from app.models.project import Project
from app.models.user import User, UserRole

# OAuth2 token URL — must match the login endpoint path
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ---------------------------------------------------------------------------
# JWT-based user dependency
# ---------------------------------------------------------------------------

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode the Bearer JWT and return the authenticated User.

    Raises:
        HTTPException 401: If the token is missing, expired, or invalid.
        HTTPException 404: If the user encoded in the token no longer exists.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exc

    user_id_str: str | None = payload.get("sub")
    if user_id_str is None:
        raise credentials_exc

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise credentials_exc

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exc

    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """Ensure the authenticated user's account is not deactivated.

    Raises:
        HTTPException 403: If the user's ``is_active`` flag is ``False``.
    """
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )
    return user


# ---------------------------------------------------------------------------
# API-key dependency (used by the ingestion endpoint)
# ---------------------------------------------------------------------------

async def get_project_by_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> Project:
    """Authenticate an SDK/agent request using the ``X-API-Key`` header.

    Resolution steps:
    1. Extract the first 12 characters of the supplied key as the prefix.
    2. Query the ``api_keys`` table by prefix (indexed).
    3. Perform constant-time hash verification against all matching active keys.
    4. Update ``last_used_at`` and return the associated ``Project``.

    Raises:
        HTTPException 401: If no valid, active key matches.
    """
    invalid_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or inactive API key.",
        headers={"WWW-Authenticate": "ApiKey"},
    )

    if len(x_api_key) < 12:
        raise invalid_exc

    prefix = x_api_key[:12]

    # Load all active keys sharing this prefix (normally exactly one)
    result = await db.execute(
        select(APIKey)
        .where(APIKey.key_prefix == prefix, APIKey.is_active.is_(True))
    )
    candidates: list[APIKey] = list(result.scalars().all())

    matched_key: APIKey | None = None
    for candidate in candidates:
        if verify_api_key(x_api_key, candidate.key_hash):
            matched_key = candidate
            break

    if matched_key is None:
        raise invalid_exc

    # Stamp the last-used timestamp (fire-and-forget; don't block response)
    matched_key.last_used_at = datetime.now(timezone.utc)
    await db.commit()

    # Load the associated project
    proj_result = await db.execute(
        select(Project).where(Project.id == matched_key.project_id)
    )
    project = proj_result.scalar_one_or_none()
    if project is None:
        raise invalid_exc

    return project


# ---------------------------------------------------------------------------
# Role-based access control factory
# ---------------------------------------------------------------------------

def require_role(*roles: UserRole) -> Callable:
    """Return a FastAPI dependency that enforces role membership.

    Args:
        *roles: One or more :class:`UserRole` values that are permitted.

    Returns:
        An ``async`` dependency callable suitable for ``Depends(...)``.

    Example::

        @router.delete(
            "/orgs/{org_id}",
            dependencies=[Depends(require_role(UserRole.owner))],
        )
        async def delete_org(...):
            ...
    """

    async def _check_role(
        user: User = Depends(get_current_active_user),
    ) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"This action requires one of the following roles: "
                    f"{[r.value for r in roles]}."
                ),
            )
        return user

    return _check_role
