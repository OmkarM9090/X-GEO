"""Repository layer: every SQL/ORM statement lives here.

Repositories are constructed with an :class:`~sqlalchemy.ext.asyncio.AsyncSession`
and never commit (the session owner — ``get_db`` or ``task_session`` — owns the
transaction boundary).
"""

from app.repositories.audit_repo import AuditRepository
from app.repositories.base import BaseRepository
from app.repositories.chunk_repo import ChunkRepository
from app.repositories.crawl_repo import CrawlRepository
from app.repositories.project_repo import ProjectRepository, ProjectStats
from app.repositories.user_repo import UserRepository

__all__ = [
    "AuditRepository",
    "BaseRepository",
    "ChunkRepository",
    "CrawlRepository",
    "ProjectRepository",
    "ProjectStats",
    "UserRepository",
]
