"""
app/schemas/common.py
=====================
Shared Pydantic utility schemas used across multiple endpoints.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

# Generic type variable for paginated item lists
T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated collection response.

    Usage::

        @router.get("/items", response_model=PaginatedResponse[ItemResponse])
        async def list_items(...):
            ...
    """

    items: list[T]
    total: int = Field(..., description="Total number of matching records.")
    page: int = Field(..., description="Current page number (1-indexed).")
    page_size: int = Field(..., description="Number of items per page.")
    pages: int = Field(..., description="Total number of pages.")


class MessageResponse(BaseModel):
    """Simple acknowledgement response."""

    message: str


class ErrorResponse(BaseModel):
    """Structured error body for 4xx / 5xx responses."""

    error: str = Field(..., description="Machine-readable error code or short message.")
    detail: str | None = Field(None, description="Human-readable explanation.")
