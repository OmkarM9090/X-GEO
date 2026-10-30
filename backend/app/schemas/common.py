"""Shared schema primitives: pagination, generic pages, error envelopes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Generic, Self, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20


@dataclass(slots=True)
class Pagination:
    """Validated pagination request (built by ``app.api.deps.get_pagination``)."""

    skip: int = 0
    limit: int = DEFAULT_PAGE_SIZE

    @property
    def offset(self) -> int:
        return self.skip


class Page(BaseModel, Generic[T]):
    """Envelope for every list endpoint."""

    model_config = ConfigDict(from_attributes=True)

    items: list[T]
    total: int = Field(ge=0)
    skip: int = Field(ge=0)
    limit: int = Field(ge=1)
    has_more: bool = False

    @classmethod
    def create(cls, items: list[T], *, total: int, skip: int, limit: int) -> Self:
        return cls(
            items=items, total=total, skip=skip, limit=limit, has_more=(skip + len(items)) < total
        )


class ErrorResponse(BaseModel):
    """Canonical error body returned by every non-2xx response.

    ``message`` is a human-readable summary (used directly by the frontend),
    ``detail`` mirrors FastAPI's native field and holds the validation list for
    ``422`` responses, and ``request_id`` correlates the response with the logs.
    """

    message: str
    code: str = "error"
    detail: Any | None = None
    request_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class MessageResponse(BaseModel):
    """Simple acknowledgement body."""

    message: str


class TimestampedModel(BaseModel):
    """Base class for read models that expose audit timestamps."""

    model_config = ConfigDict(from_attributes=True)

    id: Any
    created_at: datetime
    updated_at: datetime


__all__ = [
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "ErrorResponse",
    "MessageResponse",
    "Page",
    "Pagination",
    "TimestampedModel",
]
