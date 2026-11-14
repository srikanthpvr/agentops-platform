"""
app/schemas/eval.py
===================
Pydantic schemas for evaluation dataset and run endpoints.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# EvalDataset schemas
# ---------------------------------------------------------------------------

class EvalDatasetCreate(BaseModel):
    """Payload for creating a new evaluation dataset."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class EvalDatasetResponse(BaseModel):
    """Serialised EvalDataset returned to callers."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str | None
    schema_: dict | None = Field(None, alias="schema_")
    row_count: int
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# EvalRun schemas
# ---------------------------------------------------------------------------

class EvalRunCreate(BaseModel):
    """Payload for creating and enqueuing a new evaluation run."""

    model_config = ConfigDict(populate_by_name=True)

    dataset_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=255)
    # E.g. {"model": "gpt-4o", "temperature": 0.0, "system_prompt": "..."}
    model_config_: dict = Field(..., alias="model_config")
    # Optional separate judge model configuration
    judge_config: dict | None = None


class EvalRunResponse(BaseModel):
    """Serialised EvalRun returned to callers."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    project_id: uuid.UUID
    dataset_id: uuid.UUID
    name: str
    model_config_: dict = Field(alias="model_config")
    judge_config: dict | None
    status: str
    avg_score: float | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
