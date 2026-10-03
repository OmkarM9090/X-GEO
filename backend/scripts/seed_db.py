#!/usr/bin/env python3
"""Seed the database with one realistic demo tenant.

The script is idempotent: re-running it reuses the same user/project and
refreshes the demo audit. Use ``--reset`` to delete the demo project (with every
related audit, crawl job, chunk and simulation run) before seeding again.

What it creates:

* a demo user whose local identity matches ``POST /api/v1/auth/dev-token`` for
  the same e-mail address, so the seeded data is immediately visible;
* a project with tracked prompts and a fully populated domain-signal row;
* one *completed* audit: crawl job, clean markdown artifact, ingested chunks
  (embedded) and the full PCS explainability breakdown;
* the alignment score is computed against the tracked prompts via the same
  service used by the crawl pipeline.

Usage::

    python scripts/seed_db.py                 # create or refresh demo data
    python scripts/seed_db.py --reset         # wipe the demo project first
    python scripts/seed_db.py --email you@example.com
    python scripts/seed_db.py --json          # machine-readable summary
"""

# ruff: noqa: E402 - the backend root has to be importable before `app.*` loads.

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_settings
from app.core.database import dispose_engine, init_models, session_scope
from app.core.logging_config import configure_logging, get_logger
from app.models.audit import AuditStatus
from app.models.crawl import CrawlMethod
from app.models.domain import DomainCrawlStatus
from app.models.user import PlanTier
from app.repositories.audit_repo import AuditRepository
from app.repositories.crawl_repo import CrawlRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.user_repo import UserRepository
from app.services.audit_service import AuditService, build_scoring_input
from app.services.auth_service import dev_supabase_uid
from app.services.chunk_service import ChunkService

logger = get_logger(__name__)

DEFAULT_EMAIL = "demo@xgeo.dev"
PROJECT_NAME = "Acme Analytics"
PROJECT_DOMAIN = "https://example.com"
PROJECT_DESCRIPTION = "Seeded demo project — a B2B analytics suite competing for AI citations."

TRACKED_PROMPTS: tuple[str, ...] = (
    "best analytics platform for B2B SaaS teams",
    "how to measure AI search visibility",
    "generative engine optimization tools compared",
    "what is prompt citation share",
)

SAMPLE_MARKDOWN = """# AI Search Visibility for B2B SaaS Teams

Buyers now ask ChatGPT, Perplexity and Google's AI Overviews before they ever
open a landing page. In a 2025 benchmark of 1,200 B2B software queries, 38% of
answers cited a vendor's own documentation, while 24% cited comparison
articles. Only 12% cited the vendor's homepage.

## Why citation share beats rankings

Classic SEO counts positions; generative engines count citations. A page that
ranks first can still be quoted last if it lacks verifiable claims. Studies of
answer engines show that passages containing a statistic, a date and a named
source are 3.4x more likely to be selected as the supporting citation.

## How the Prompt Citation Score works

The Prompt Citation Score (PCS) combines four weighted components:

| Component | Weight | What it measures |
| --- | --- | --- |
| Technical readiness | 0.35 | crawlability, metadata, structured data |
| Semantic alignment | 0.30 | cosine similarity to tracked prompts |
| Evidentiary density | 0.20 | numbers, dates, units, quotes per 100 words |
| Machine readability | 0.15 | headings, lists, tables, short paragraphs |

Numbers matter: audits that lifted evidentiary density from 0.4 to 0.8 saw
citation share improve by 19 percentage points within 60 days.

## Practical checklist

1. Publish one canonical URL per topic and keep it stable for at least 90 days.
2. Add JSON-LD (`Article`, `FAQPage`, `Product`) so engines can parse claims.
3. Cite primary sources inline, e.g. "according to Gartner (2024)".
4. Keep paragraphs under 120 words and prefer lists for multi-step instructions.
5. Refresh statistics quarterly — stale figures are the most common reason a
   page loses its citation to a competitor.

> "The winning page is rarely the longest one; it is the one whose claims can be
> verified in a single pass." — internal analysis, 2025

## Measuring progress

Track citation share per prompt, not per keyword. A practical cadence is weekly
sampling across 20-50 prompts, comparing your domain against three competitors.
Report the delta, the sampled engine, and the exact passage that was cited.
"""

PAGE_METADATA = SimpleNamespace(
    url=f"{PROJECT_DOMAIN}/guides/ai-search-visibility",
    title="AI Search Visibility for B2B SaaS Teams",
    meta_description=(
        "How B2B SaaS teams measure and improve citation share in ChatGPT, "
        "Perplexity and AI Overviews."
    ),
    canonical_url=f"{PROJECT_DOMAIN}/guides/ai-search-visibility",
    lang="en",
    json_ld_types=("Article", "FAQPage"),
    headings=("AI Search Visibility for B2B SaaS Teams", "Why citation share beats rankings"),
    has_json_ld=True,
    has_canonical=True,
    has_meta_description=True,
    heading_structure_valid=True,
    has_sitemap=True,
    has_lang=True,
    has_viewport=True,
    has_lists=True,
    has_tables=True,
    boilerplate_ratio=0.08,
    avg_paragraph_words=42.0,
    semantic_html_score=1.0,
    external_link_count=3,
)

JSON_LD = {
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "AI Search Visibility for B2B SaaS Teams",
    "datePublished": "2025-09-02",
    "author": {"@type": "Organization", "name": "Acme Analytics"},
}


async def _find_project(projects: ProjectRepository, user_id: uuid.UUID) -> Any | None:
    """First project of ``user_id`` whose domain matches the demo domain."""
    items, _total = await projects.list_for_user(user_id, limit=100)
    for project in items:
        if project.domain_url == PROJECT_DOMAIN:
            return project
    return None


async def seed(*, email: str = DEFAULT_EMAIL, reset: bool = False) -> dict[str, Any]:
    """Create (or refresh) the demo tenant and return a summary dictionary."""
    settings = get_settings()
    summary: dict[str, Any] = {"email": email, "project_domain": PROJECT_DOMAIN}

    async with session_scope() as session:
        users = UserRepository(session)
        projects = ProjectRepository(session)
        audits = AuditRepository(session)
        crawls = CrawlRepository(session)

        user = await users.get_by_email(email)
        if user is None:
            user = await users.create_from_identity(
                supabase_uid=dev_supabase_uid(email),
                email=email,
                full_name="Demo Tenant",
                plan_tier=PlanTier.PRO.value,
            )
        elif user.plan_tier != PlanTier.PRO.value:
            await users.set_plan(user.id, PlanTier.PRO.value)
        summary["user_id"] = str(user.id)

        project = await _find_project(projects, user.id)
        if project is not None and reset:
            await audits.delete_where(project_id=project.id)
            await projects.delete_where(id=project.id)
            project = None

        if project is None:
            project = await projects.create(
                user_id=user.id,
                name=PROJECT_NAME,
                domain_url=PROJECT_DOMAIN,
                description=PROJECT_DESCRIPTION,
            )
        summary["project_id"] = str(project.id)

        await audits.upsert_prompts(project.id, list(TRACKED_PROMPTS))
        domain = await audits.get_or_create_domain(
            project_id=project.id,
            url=PROJECT_DOMAIN,
            sitemap_url=f"{PROJECT_DOMAIN}/sitemap.xml",
        )
        await audits.update_domain_signals(
            domain.id,
            crawl_status=DomainCrawlStatus.COMPLETED.value,
            last_crawled_at=datetime.now(tz=UTC),
            sitemap_url=f"{PROJECT_DOMAIN}/sitemap.xml",
            robots_txt="User-agent: *\nAllow: /\nSitemap: https://example.com/sitemap.xml\n",
            has_json_ld=True,
            has_sitemap=True,
            heading_structure_valid=True,
            meta_description_present=True,
            canonical_set=True,
            robots_txt_allows_crawl=True,
        )

        audit = await audits.create(
            project_id=project.id,
            domain_id=domain.id,
            target_url=PAGE_METADATA.url,
            status=AuditStatus.CRAWLING.value,
        )
        summary["audit_id"] = str(audit.id)

        job = await crawls.create(
            audit_id=audit.id,
            url=PAGE_METADATA.url,
            method=CrawlMethod.HTTPX.value,
        )
        await crawls.mark_running(job.id)
        await crawls.mark_completed(
            job.id,
            http_status_code=200,
            content_type="text/html; charset=utf-8",
            response_time_ms=412,
            response_size_bytes=48_120,
            robots_txt_allowed=True,
            method=CrawlMethod.HTTPX.value,
        )
        summary["crawl_job_id"] = str(job.id)

        word_count = len(SAMPLE_MARKDOWN.split())
        await audits.save_crawl_artifact(
            audit.id,
            clean_markdown=SAMPLE_MARKDOWN,
            word_count=word_count,
            json_ld_data=JSON_LD,
        )

        ingest = await ChunkService(session, settings=settings).ingest_markdown(
            audit.id, SAMPLE_MARKDOWN, embed=True
        )
        summary["chunks_created"] = ingest.chunks_created
        summary["chunks_embedded"] = ingest.chunks_embedded

        scoring_input = build_scoring_input(
            PAGE_METADATA,
            markdown=SAMPLE_MARKDOWN,
            word_count=word_count,
            target_url=PAGE_METADATA.url,
            response_time_ms=412,
        )
        result = await AuditService(session, settings=settings).score_audit(
            audit.id, data=scoring_input, metadata=PAGE_METADATA
        )
        await AuditService(session, settings=settings).mark_completed(audit.id)
        summary["pcs_score"] = round(result.pcs, 4) if result.pcs is not None else None
        summary["technical_readiness"] = result.technical_readiness
        summary["evidentiary_density"] = result.evidentiary_density
        summary["machine_readability"] = result.machine_readability
        summary["semantic_alignment"] = result.semantic_alignment

        logger.info("seed.completed", **{k: v for k, v in summary.items() if k != "email"})

    summary["access_token_command"] = (
        "curl -s -X POST http://localhost:8000/api/v1/auth/dev-token "
        "-H 'Content-Type: application/json' -d '{\"email\": \"" + email + "\"}'"
    )
    return summary


def _print_human(summary: dict[str, Any]) -> None:
    """Friendly summary for interactive use."""
    print("\nX-GEO demo data ready\n" + "-" * 22)
    print(f"  user        {summary['email']}  ({summary['user_id']})")
    print(f"  project     {PROJECT_NAME} — {summary['project_domain']}  ({summary['project_id']})")
    print(f"  audit       {summary['audit_id']}   PCS {summary['pcs_score']}")
    print(
        f"  chunks      {summary['chunks_created']} created, {summary['chunks_embedded']} embedded"
    )
    print(f"  crawl job   {summary['crawl_job_id']}\n")
    print("Try it:")
    print("  1. mint a token (DEBUG only):")
    print(f"       {summary['access_token_command']}")
    print("  2. call the API with it:")
    print('       curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/projects')
    print("  3. explore the docs:  http://localhost:8000/api/docs\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed X-GEO demo data.")
    parser.add_argument(
        "--email", default=DEFAULT_EMAIL, help=f"demo user e-mail (default: {DEFAULT_EMAIL})"
    )
    parser.add_argument(
        "--reset", action="store_true", help="delete the demo project before seeding"
    )
    parser.add_argument("--json", action="store_true", help="print the summary as JSON")
    parser.add_argument(
        "--skip-create-tables",
        action="store_true",
        help="do not run create_all (use when migrations own the schema)",
    )
    parser.add_argument("--quiet", action="store_true", help="only report errors")
    args = parser.parse_args(argv)

    configure_logging(force=True)

    async def _run() -> dict[str, Any]:
        if not args.skip_create_tables:
            await init_models()
        try:
            return await seed(email=args.email, reset=args.reset)
        finally:
            await dispose_engine()

    try:
        summary = asyncio.run(_run())
    except Exception as exc:  # pragma: no cover - CLI boundary
        print(f"Seeding failed: {exc}", file=sys.stderr)
        print(
            "Hint: is PostgreSQL running?  python scripts/dev_db.py start",
            file=sys.stderr,
        )
        return 1

    if args.json:
        print(json.dumps(summary, indent=2, default=str))
    elif not args.quiet:
        _print_human(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
