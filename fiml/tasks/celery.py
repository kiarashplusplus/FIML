"""
Celery application configuration
"""

from celery import Celery

from fiml.core.config import settings

# Create Celery app
celery_app = Celery(
    "fiml",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "fiml.tasks.data_tasks",
        "fiml.tasks.analysis_tasks",
    ],
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "update-provider-health-every-5-minutes": {
        "task": "fiml.tasks.data_tasks.update_provider_health",
        "schedule": 300.0,  # 5 minutes
    },
    "refresh-cache-hourly": {
        "task": "fiml.tasks.data_tasks.refresh_cache",
        "schedule": 3600.0,  # 1 hour
        "args": (100,),  # Refresh top 100 cached items
    },
}

if __name__ == "__main__":
    celery_app.start()
