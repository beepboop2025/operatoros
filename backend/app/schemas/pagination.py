"""Shared paginated response schema and helper."""

from __future__ import annotations

from typing import Any, Generic, List, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response wrapper.

    All list endpoints should use this schema to ensure consistent
    JSON structure: ``{"items": [...], "total": N, "page": 1, "page_size": 20}``.
    """

    items: List[Any] = Field(default_factory=list)
    total: int = Field(0, ge=0)
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1)


def paginated_response(
    items: list,
    total: int,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Build a standardised paginated response dict.

    Use this from route handlers that don't use the Pydantic model directly.
    """
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
