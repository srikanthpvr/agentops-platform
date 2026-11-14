"""
app/main.py
===========
FastAPI application factory for the AgentOps platform.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address
    limiter = Limiter(key_func=get_remote_address, default_limits=["1000/minute"])
    HAS_SLOWAPI = True
except ImportError:
    limiter = None
    HAS_SLOWAPI = False

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Run DB table creation on startup
    await init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AgentOps Platform: AI Agent Observability, Evaluation & Governance",
    lifespan=lifespan,
)

if HAS_SLOWAPI and limiter:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENVIRONMENT == "development" else ["https://app.agentops.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "ok",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }

# Include API v1 routes
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)
