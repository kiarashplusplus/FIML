"""
Celery tasks for session management
"""

from datetime import datetime, timedelta

from celery import shared_task

from fiml.core.config import settings
from fiml.core.logging import get_logger
from fiml.sessions.analytics import SessionAnalytics
from fiml.sessions.store import get_session_store

logger = get_logger(__name__)


@shared_task(name="fiml.sessions.cleanup_expired_sessions")
async def cleanup_expired_sessions() -> dict:
    """
    Cleanup expired sessions task

    Archives expired sessions to PostgreSQL and removes from Redis
    Runs on schedule (hourly by default)

    Returns:
        Task result with cleanup statistics
    """
    try:
        logger.info("Starting session cleanup task")

        session_store = await get_session_store()
        cleaned_count = await session_store.cleanup_expired_sessions()

        logger.info(f"Session cleanup completed: {cleaned_count} sessions archived")

        return {
            "status": "success",
            "cleaned_count": cleaned_count,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Session cleanup task failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@shared_task(name="fiml.sessions.delete_old_archived_sessions")
async def delete_old_archived_sessions() -> dict:
    """
    Delete archived sessions older than retention period

    Removes archived sessions from PostgreSQL based on retention policy
    Runs daily

    Returns:
        Task result with deletion statistics
    """
    try:
        logger.info("Starting old session deletion task")

        from sqlalchemy import delete

        from fiml.sessions.db import SessionRecord

        session_store = await get_session_store()

        if not session_store._session_maker:
            raise RuntimeError("SessionStore not initialized")

        # Calculate cutoff date based on retention policy
        cutoff_date = datetime.utcnow() - timedelta(days=settings.session_retention_days)

        async with session_store._session_maker() as db_session:
            # Delete old archived sessions
            stmt = delete(SessionRecord).where(
                SessionRecord.is_archived == True,
                SessionRecord.archived_at < cutoff_date,
            )

            result = await db_session.execute(stmt)
            await db_session.commit()

            deleted_count = result.rowcount

        logger.info(f"Deleted {deleted_count} old archived sessions")

        return {
            "status": "success",
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
            "retention_days": settings.session_retention_days,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Old session deletion task failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@shared_task(name="fiml.sessions.generate_session_metrics")
async def generate_session_metrics() -> dict:
    """
    Generate session analytics metrics

    Processes recent sessions and generates aggregated metrics
    Runs daily

    Returns:
        Task result with metrics summary
    """
    try:
        logger.info("Starting session metrics generation task")

        from sqlalchemy import select

        from fiml.sessions.db import SessionRecord

        session_store = await get_session_store()

        if not session_store._session_maker:
            raise RuntimeError("SessionStore not initialized")

        analytics = SessionAnalytics(session_store._session_maker)

        # Get recently archived sessions that don't have metrics yet
        async with session_store._session_maker() as db_session:
            # Find archived sessions from last 24 hours
            cutoff = datetime.utcnow() - timedelta(hours=24)
            stmt = select(SessionRecord).where(
                SessionRecord.is_archived == True,
                SessionRecord.archived_at >= cutoff,
            )

            result = await db_session.execute(stmt)
            records = result.scalars().all()

            # Record metrics for each session
            metrics_count = 0
            for record in records:
                session = session_store._session_from_record(record)
                await analytics.record_session_metrics(session)
                metrics_count += 1

        logger.info(f"Generated metrics for {metrics_count} sessions")

        return {
            "status": "success",
            "metrics_generated": metrics_count,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Session metrics generation task failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


# Celery beat schedule configuration
CELERY_BEAT_SCHEDULE = {
    "cleanup-expired-sessions": {
        "task": "fiml.sessions.cleanup_expired_sessions",
        "schedule": settings.session_cleanup_interval_minutes * 60.0,  # Convert to seconds
        "options": {"expires": 300},  # Task expires after 5 minutes if not executed
    },
    "delete-old-archived-sessions": {
        "task": "fiml.sessions.delete_old_archived_sessions",
        "schedule": 86400.0,  # Daily (24 hours)
        "options": {"expires": 3600},  # Task expires after 1 hour
    },
    "generate-session-metrics": {
        "task": "fiml.sessions.generate_session_metrics",
        "schedule": 86400.0,  # Daily
        "options": {"expires": 3600},
    },
}
