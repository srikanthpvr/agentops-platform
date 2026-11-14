"""
app/api/v1/auth.py
==================
Authentication endpoints: register, login, and whoami.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.security import create_access_token, hash_password, verify_password
from app.models.org import Org
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new organisation and its first owner user.",
)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Create a new :class:`Org` and an ``owner``-role :class:`User`.

    Returns a JWT access token so the caller is immediately authenticated
    without a separate login round-trip.

    Raises:
        HTTPException 409: If the email address is already registered.
    """
    # Reject duplicate emails
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    # Create the Org first
    org = Org(name=payload.org_name)
    db.add(org)
    await db.flush()  # populate org.id without committing yet

    # Create the owner user
    user = User(
        org_id=org.id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=UserRole.owner,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Issue a token
    token = create_access_token(
        data={"sub": str(user.id), "org_id": str(org.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate with email and password, receive a JWT.",
)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Validate credentials and return a Bearer access token.

    Raises:
        HTTPException 401: If the email is not found or the password is wrong.
    """
    result = await db.execute(select(User).where(User.email == payload.email))
    user: User | None = result.scalar_one_or_none()

    # Fail in constant time — always call verify_password even if user is None
    # to prevent timing-based email enumeration attacks.
    dummy_hash = "$2b$12$xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    if user is None:
        verify_password(payload.password, dummy_hash)  # discard result
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    token = create_access_token(
        data={"sub": str(user.id), "org_id": str(user.org_id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get(
    "/me",
    summary="Return the currently authenticated user's profile.",
)
async def me(
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Return basic profile information for the authenticated user."""
    return {
        "id": str(current_user.id),
        "org_id": str(current_user.org_id),
        "email": current_user.email,
        "role": current_user.role.value,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat(),
    }
