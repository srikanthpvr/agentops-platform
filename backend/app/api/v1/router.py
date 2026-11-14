"""
app/api/v1/router.py
====================
Main v1 API router aggregating all domain endpoints.
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.evals import router as evals_router
from app.api.v1.governance import router as governance_router
from app.api.v1.projects import router as projects_router
from app.api.v1.traces import router as traces_router

api_v1_router = APIRouter()

# Authentication
api_v1_router.include_router(auth_router)

# Projects & API Keys
api_v1_router.include_router(projects_router)

# Traces & Spans (includes /ingest/traces and /projects/{project_id}/traces)
api_v1_router.include_router(traces_router)

# Evaluations
api_v1_router.include_router(evals_router)

# Governance & Policies
api_v1_router.include_router(governance_router)
