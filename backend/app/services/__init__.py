"""Service layer: all business logic lives here.

Layer contract
--------------
* routes validate input with Pydantic and delegate;
* services own decisions, orchestration and transactions;
* repositories own SQL;
* models own the schema; schemas own the wire format.
"""

from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.chunk_service import ChunkService
from app.services.crawl_service import CrawlService
from app.services.project_service import ProjectService

__all__ = [
    "AuditService",
    "AuthService",
    "ChunkService",
    "CrawlService",
    "ProjectService",
]
