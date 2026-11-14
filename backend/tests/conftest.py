"""
backend/tests/conftest.py
=========================
Pytest fixtures and configuration for backend async tests.
"""

import asyncio
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import hash_password, generate_api_key
from app.main import app
from app.models.org import Org, OrgTier
from app.models.user import User, UserRole
from app.models.project import Project
from app.models.api_key import APIKey

# Test in-memory SQLite database
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestingSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)





@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create tables before tests and drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Test client with db override."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_org(db_session: AsyncSession) -> Org:
    org = Org(name="Acme AI Corp", tier=OrgTier.pro)
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, test_org: Org) -> User:
    user = User(
        org_id=test_org.id,
        email="test@example.com",
        hashed_password=hash_password("SuperSecret123!"),
        role=UserRole.owner,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_project(db_session: AsyncSession, test_org: Org) -> Project:
    project = Project(
        org_id=test_org.id,
        name="Support Agent",
        description="Customer support automated agent",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def test_api_key(db_session: AsyncSession, test_project: Project) -> tuple[str, APIKey]:
    full_key, prefix, hashed = generate_api_key()
    api_key_obj = APIKey(
        project_id=test_project.id,
        name="Default Test Key",
        key_prefix=prefix,
        key_hash=hashed,
    )
    db_session.add(api_key_obj)
    await db_session.commit()
    await db_session.refresh(api_key_obj)
    return full_key, api_key_obj
