"""Monte-Carlo simulation tasks — **Phase 3 stubs**.

The tables (``simulation_runs``, ``citation_logs``) and the task signatures ship
now so the worker, queues and API contracts are already wired. Phase 3 implements
the sampling loop (``N`` runs per prompt at temperature ``T`` against each
engine) and Phase 4 adds NLI verification of the cited claims.

Each stub returns a structured ``{"status": "not_implemented", ...}`` payload
rather than raising, so a premature dispatch cannot poison the queue with
exceptions while still being observable in logs and task results.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.config import get_settings
from app.core.logging_config import configure_logging, get_logger
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)
settings = get_settings()

SIMULATION_QUEUE = "xgeo.simulation"
PHASE = 3


async def run_simulation_async(
    audit_id: str,
    prompt_id: str,
    *,
    runs: int = 10,
    temperatures: tuple[float, ...] = (0.0, 0.7, 1.0),
) -> dict[str, Any]:
    """Placeholder for the Monte-Carlo sampling loop (Phase 3)."""
    logger.info(
        "simulation.not_implemented",
        audit_id=audit_id,
        prompt_id=prompt_id,
        runs=runs,
        temperatures=list(temperatures),
        phase=PHASE,
    )
    return {
        "status": "not_implemented",
        "phase": PHASE,
        "audit_id": audit_id,
        "prompt_id": prompt_id,
        "planned_runs": runs * len(temperatures),
        "detail": "Simulation engine arrives in Phase 3; schema and queue are ready.",
    }


@celery_app.task(name="app.tasks.simulation_tasks.run_simulation")
def run_simulation(
    audit_id: str,
    prompt_id: str,
    runs: int = 10,
    temperatures: list[float] | None = None,
) -> dict[str, Any]:
    """Queue entry point for a simulation batch (stub)."""
    configure_logging(settings, force=True)
    return asyncio.run(
        run_simulation_async(
            audit_id,
            prompt_id,
            runs=runs,
            temperatures=tuple(temperatures) if temperatures else (0.0, 0.7, 1.0),
        )
    )


async def aggregate_citations_async(audit_id: str) -> dict[str, Any]:
    """Placeholder for PWC aggregation across citation logs (Phase 3)."""
    logger.info("simulation.aggregate_not_implemented", audit_id=audit_id, phase=PHASE)
    return {
        "status": "not_implemented",
        "phase": PHASE,
        "audit_id": audit_id,
        "detail": "Position-weighted citation scoring arrives with the Phase 3 simulator.",
    }


@celery_app.task(name="app.tasks.simulation_tasks.aggregate_citations")
def aggregate_citations(audit_id: str) -> dict[str, Any]:
    """Aggregate citation statistics for an audit (stub)."""
    return asyncio.run(aggregate_citations_async(audit_id))


async def verify_citations_async(simulation_run_id: str) -> dict[str, Any]:
    """Placeholder for NLI entailment verification of citations (Phase 4)."""
    logger.info("simulation.nli_not_implemented", simulation_run_id=simulation_run_id, phase=4)
    return {
        "status": "not_implemented",
        "phase": 4,
        "simulation_run_id": simulation_run_id,
        "detail": "NLI verification arrives in Phase 4.",
    }


@celery_app.task(name="app.tasks.simulation_tasks.verify_citations")
def verify_citations(simulation_run_id: str) -> dict[str, Any]:
    """Verify that cited sentences entail the source claims (stub)."""
    return asyncio.run(verify_citations_async(simulation_run_id))


__all__ = [
    "PHASE",
    "SIMULATION_QUEUE",
    "aggregate_citations",
    "aggregate_citations_async",
    "run_simulation",
    "run_simulation_async",
    "verify_citations",
    "verify_citations_async",
]
