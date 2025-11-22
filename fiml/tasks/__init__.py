"""
Celery tasks for asynchronous processing
"""

from fiml.tasks.celery import celery_app
from fiml.tasks.data_tasks import (
    fetch_historical_data,
    refresh_cache,
    update_provider_health,
)
from fiml.tasks.analysis_tasks import (
    run_deep_analysis,
    run_scheduled_analysis,
)

__all__ = [
    "celery_app",
    "fetch_historical_data",
    "refresh_cache",
    "update_provider_health",
    "run_deep_analysis",
    "run_scheduled_analysis",
]
