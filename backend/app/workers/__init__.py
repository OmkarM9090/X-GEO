"""Celery worker entrypoints.

Deployments can either point Celery at the tasks package directly::

    celery -A app.tasks.celery_app:celery_app worker -Q xgeo.crawl,xgeo.simulation

or at this package, which re-exports the same application and task modules and
therefore registers every task::

    celery -A app.workers worker -Q xgeo.crawl,xgeo.simulation
"""

from __future__ import annotations

from app.tasks import crawl_tasks, simulation_tasks
from app.tasks.celery_app import celery_app

__all__ = ["celery_app", "crawl_tasks", "simulation_tasks"]
