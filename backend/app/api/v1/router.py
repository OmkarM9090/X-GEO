"""Aggregate router for API v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import audits, auth, crawls, health, projects

api_v1_router = APIRouter()

api_v1_router.include_router(health.router, prefix="/health", tags=["Health"])
api_v1_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_v1_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_v1_router.include_router(audits.router, prefix="/audits", tags=["Audits"])
api_v1_router.include_router(crawls.router, prefix="/crawls", tags=["Crawls"])

__all__ = ["api_v1_router"]
