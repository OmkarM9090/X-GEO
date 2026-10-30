"""CrawlJob — one fetch attempt of one URL for an audit."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    false,
    true,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class CrawlStatus(StrEnum):
    """Crawl job lifecycle states."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


CRAWL_STATUS_VALUES: tuple[str, ...] = tuple(status.value for status in CrawlStatus)


class CrawlMethod(StrEnum):
    """Which fetcher produced the response."""

    SCRAPY = "scrapy"
    PLAYWRIGHT = "playwright"
    HTTPX = "httpx"


CRAWL_METHOD_VALUES: tuple[str, ...] = tuple(method.value for method in CrawlMethod)


class CrawlJob(Base, UUIDMixin, TimestampMixin):
    """Transport-level record of fetching a URL.

    Kept separate from :class:`~app.models.audit.Audit` so retries, SPA
    fallbacks and response metadata are auditable over time.
    """

    __tablename__ = "crawl_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
            name="status_valid",
        ),
        CheckConstraint("method IN ('scrapy', 'playwright', 'httpx')", name="method_valid"),
        CheckConstraint("retry_count >= 0", name="retry_count_non_negative"),
        Index("ix_crawl_jobs_audit_status", "audit_id", "status"),
        Index("ix_crawl_jobs_status_created", "status", "created_at"),
    )

    audit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    method: Mapped[str] = mapped_column(
        String(32),
        default=CrawlMethod.SCRAPY.value,
        server_default=CrawlMethod.SCRAPY.value,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=CrawlStatus.PENDING.value,
        server_default=CrawlStatus.PENDING.value,
        nullable=False,
    )

    http_status_code: Mapped[int | None] = mapped_column(Integer)
    content_type: Mapped[str | None] = mapped_column(String(255))
    response_time_ms: Mapped[int | None] = mapped_column(Integer)
    response_size_bytes: Mapped[int | None] = mapped_column(Integer)

    # --- SPA detection --------------------------------------------------------
    is_spa_detected: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    playwright_fallback_used: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    robots_txt_allowed: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    audit = relationship("Audit", back_populates="crawl_jobs", lazy="raise")


__all__ = ["CRAWL_METHOD_VALUES", "CRAWL_STATUS_VALUES", "CrawlJob", "CrawlMethod", "CrawlStatus"]
