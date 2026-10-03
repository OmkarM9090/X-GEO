"""Domain — an individual host/URL discovered for a project."""

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
    String,
    Text,
    UniqueConstraint,
    false,
    true,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class DomainCrawlStatus(StrEnum):
    """Lifecycle of a domain within the crawl pipeline."""

    PENDING = "pending"
    CRAWLING = "crawling"
    COMPLETED = "completed"
    FAILED = "failed"


DOMAIN_CRAWL_STATUS_VALUES: tuple[str, ...] = tuple(status.value for status in DomainCrawlStatus)


class Domain(Base, UUIDMixin, TimestampMixin):
    """A crawlable URL plus the cached technical-readiness signals for it."""

    __tablename__ = "domains"
    __table_args__ = (
        UniqueConstraint("project_id", "url", name="project_url"),
        Index("ix_domains_project_status", "project_id", "crawl_status"),
        CheckConstraint(
            "crawl_status IN ('pending', 'crawling', 'completed', 'failed')",
            name="crawl_status_valid",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    sitemap_url: Mapped[str | None] = mapped_column(String(2048))
    robots_txt: Mapped[str | None] = mapped_column(Text)
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    crawl_status: Mapped[str] = mapped_column(
        String(32),
        default=DomainCrawlStatus.PENDING.value,
        server_default=DomainCrawlStatus.PENDING.value,
        nullable=False,
    )

    # --- Technical audit cache (refreshed on every crawl) -------------------
    has_json_ld: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    has_sitemap: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    heading_structure_valid: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    meta_description_present: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    canonical_set: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    robots_txt_allows_crawl: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )

    project = relationship("Project", back_populates="domains", lazy="raise")
    audits = relationship(
        "Audit",
        back_populates="domain",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )


__all__ = ["DOMAIN_CRAWL_STATUS_VALUES", "Domain", "DomainCrawlStatus"]
