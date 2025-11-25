"""
Session analytics and metrics tracking
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from fiml.core.logging import get_logger
from fiml.sessions.db import SessionMetrics
from fiml.sessions.models import Session

logger = get_logger(__name__)

# Prometheus metrics (optional)
try:
    from prometheus_client import Counter, Gauge, Histogram

    PROMETHEUS_AVAILABLE = True

    # Session metrics
    SESSION_CREATED = Counter(
        "fiml_sessions_created_total",
        "Total sessions created",
        ["session_type"]
    )

    SESSION_ACTIVE = Gauge(
        "fiml_sessions_active_total",
        "Number of active sessions"
    )

    SESSION_ABANDONED = Counter(
        "fiml_sessions_abandoned_total",
        "Total abandoned sessions",
        ["session_type"]
    )

    SESSION_DURATION = Histogram(
        "fiml_session_duration_seconds",
        "Session duration in seconds",
        ["session_type"],
        buckets=[10, 30, 60, 120, 300, 600, 1800, 3600]
    )

    SESSION_QUERIES = Histogram(
        "fiml_session_queries_total",
        "Number of queries per session",
        ["query_type"],
        buckets=[1, 5, 10, 20, 50, 100, 200]
    )

except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not available - session metrics export disabled")


class SessionAnalytics:
    """
    Track and analyze session usage metrics

    Provides insights into:
    - Session duration patterns
    - Query patterns
    - Asset analysis trends
    - Abandonment rates
    """

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker
        self.enable_prometheus = PROMETHEUS_AVAILABLE

    async def record_session_metrics(self, session: Session) -> None:
        """
        Record metrics for a completed/archived session

        Args:
            session: Session to record metrics for
        """
        try:
            async with self._session_maker() as db_session:
                # Calculate metrics
                duration_seconds = int(session.duration.total_seconds())
                avg_query_time = None

                if session.state.history.queries:
                    total_time = sum(
                        q.execution_time_ms or 0 for q in session.state.history.queries
                    )
                    avg_query_time = str(total_time / len(session.state.history.queries))

                # Create metrics record
                metrics = SessionMetrics(
                    session_id=session.id,
                    user_id=session.user_id,
                    session_type=session.type.value,
                    created_at=session.created_at,
                    duration_seconds=duration_seconds,
                    total_queries=session.state.history.total_queries,
                    cache_hit_rate=str(session.state.history.cache_hit_rate),
                    avg_query_time_ms=avg_query_time,
                    assets_analyzed=session.assets,
                    query_type_summary=session.state.history.get_query_types_summary(),
                    completed_normally=not session.is_expired,
                    abandoned=session.is_expired and session.state.history.total_queries < 2,
                )

                db_session.add(metrics)
                await db_session.commit()

                logger.info(
                    f"Recorded metrics for session {session.id}",
                    queries=session.state.history.total_queries,
                    duration=duration_seconds,
                )

        except Exception as e:
            logger.error(f"Failed to record session metrics: {e}")

    async def get_session_stats(
        self,
        user_id: Optional[str] = None,
        session_type: Optional[str] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get aggregated session statistics

        Args:
            user_id: Filter by user (optional)
            session_type: Filter by type (optional)
            days: Number of days to analyze

        Returns:
            Dictionary of statistics
        """
        try:
            async with self._session_maker() as db_session:
                # Build query for session metrics
                cutoff_date = datetime.now(UTC) - timedelta(days=days)
                query = select(SessionMetrics).where(SessionMetrics.created_at >= cutoff_date)

                if user_id:
                    query = query.where(SessionMetrics.user_id == user_id)
                if session_type:
                    query = query.where(SessionMetrics.session_type == session_type)

                result = await db_session.execute(query)
                metrics = result.scalars().all()

                # Get active and archived session counts from SessionRecord
                from fiml.sessions.db import SessionRecord

                active_query = select(func.count(SessionRecord.id)).where(
                    ~SessionRecord.is_archived,
                    SessionRecord.expires_at > datetime.now(UTC),
                )
                archived_query = select(func.count(SessionRecord.id)).where(
                    SessionRecord.is_archived,
                    SessionRecord.created_at >= cutoff_date,
                )

                if user_id:
                    active_query = active_query.where(SessionRecord.user_id == user_id)
                    archived_query = archived_query.where(SessionRecord.user_id == user_id)

                active_result = await db_session.execute(active_query)
                active_sessions = active_result.scalar() or 0

                archived_result = await db_session.execute(archived_query)
                archived_sessions = archived_result.scalar() or 0

                if not metrics:
                    # Return default analytics for new users
                    return {
                        "total_sessions": 0,
                        "active_sessions": active_sessions,
                        "archived_sessions": archived_sessions,
                        "total_queries": 0,
                        "avg_duration_seconds": 0.0,
                        "avg_queries_per_session": 0.0,
                        "abandonment_rate": 0.0,
                        "period_days": days,
                        "user_id": user_id,
                        "session_type": session_type,
                        "top_assets": [],
                        "query_type_distribution": {},
                        "session_type_breakdown": {},
                        "popular_tags": [],
                        "message": "No session metrics available yet. Create sessions to start tracking analytics.",
                    }

                # Calculate statistics
                total_sessions = len(metrics)
                total_queries = sum(m.total_queries for m in metrics)
                total_duration = sum(m.duration_seconds for m in metrics)
                abandoned_count = sum(1 for m in metrics if m.abandoned)

                avg_duration = total_duration / total_sessions if total_sessions > 0 else 0
                avg_queries = total_queries / total_sessions if total_sessions > 0 else 0
                abandonment_rate = (
                    abandoned_count / total_sessions if total_sessions > 0 else 0
                )

                # Most analyzed assets
                all_assets: Dict[str, int] = {}
                for m in metrics:
                    for asset in m.assets_analyzed:
                        all_assets[asset] = all_assets.get(asset, 0) + 1

                top_assets = sorted(all_assets.items(), key=lambda x: x[1], reverse=True)[:10]

                # Query type distribution
                all_query_types: Dict[str, int] = {}
                for m in metrics:
                    for qtype, count in m.query_type_summary.items():
                        all_query_types[qtype] = all_query_types.get(qtype, 0) + count

                # Session type breakdown
                session_type_counts: Dict[str, int] = {}
                for m in metrics:
                    session_type_counts[m.session_type] = session_type_counts.get(m.session_type, 0) + 1

                # Get popular tags from archived sessions
                tags_query = select(SessionRecord.tags).where(
                    SessionRecord.is_archived,
                    SessionRecord.created_at >= cutoff_date,
                )
                if user_id:
                    tags_query = tags_query.where(SessionRecord.user_id == user_id)

                tags_result = await db_session.execute(tags_query)
                all_tags: Dict[str, int] = {}
                for row in tags_result.scalars():
                    if row:
                        for tag in row:
                            all_tags[tag] = all_tags.get(tag, 0) + 1

                popular_tags = sorted(all_tags.items(), key=lambda x: x[1], reverse=True)[:10]

                return {
                    "total_sessions": total_sessions,
                    "active_sessions": active_sessions,
                    "archived_sessions": archived_sessions,
                    "total_queries": total_queries,
                    "avg_duration_seconds": round(avg_duration, 2),
                    "avg_queries_per_session": round(avg_queries, 2),
                    "abandonment_rate": round(abandonment_rate, 4),
                    "period_days": days,
                    "user_id": user_id,
                    "session_type": session_type,
                    "top_assets": [{"symbol": symbol, "count": count} for symbol, count in top_assets],
                    "query_type_distribution": all_query_types,
                    "session_type_breakdown": session_type_counts,
                    "popular_tags": [{"tag": tag, "count": count} for tag, count in popular_tags],
                }

        except Exception as e:
            logger.error(f"Failed to get session stats: {e}")
            raise

    async def get_user_session_summary(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get session summary for specific user

        Args:
            user_id: User identifier
            days: Number of days to analyze

        Returns:
            User session summary
        """
        stats = await self.get_session_stats(user_id=user_id, days=days)

        try:
            async with self._session_maker() as db_session:
                # Get session type breakdown
                cutoff_date = datetime.now(UTC) - timedelta(days=days)
                query = (
                    select(
                        SessionMetrics.session_type,
                        func.count(SessionMetrics.id).label("count"),
                    )
                    .where(SessionMetrics.user_id == user_id)
                    .where(SessionMetrics.created_at >= cutoff_date)
                    .group_by(SessionMetrics.session_type)
                )

                result = await db_session.execute(query)
                type_breakdown = {row.session_type: row.count for row in result}

                stats["session_type_breakdown"] = type_breakdown
                return stats

        except Exception as e:
            logger.error(f"Failed to get user session summary: {e}")
            return stats

    async def export_session_metrics(
        self,
        format: str = "json",
        user_id: Optional[str] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Export session metrics in various formats

        Args:
            format: Export format (json, csv)
            user_id: Filter by user (optional)
            days: Number of days to export

        Returns:
            Exported metrics data
        """
        stats = await self.get_session_stats(user_id=user_id, days=days)

        if format == "json":
            return stats
        elif format == "csv":
            # Could be implemented to return CSV format
            return stats
        else:
            raise ValueError(f"Unsupported export format: {format}")
