"""Celery application and task definitions.

Importing this package does **not** import the task modules (they pull in the
service layer); use the Celery ``include`` list or import them explicitly::

    from app.tasks.celery_app import celery_app
    from app.tasks.crawl_tasks import run_crawl_job
"""

from app.tasks.celery_app import celery_app

__all__ = ["celery_app"]
