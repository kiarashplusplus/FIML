"""
Session analytics and metrics tracking
"""

from datetime import datetime, timedelta
from typing import Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from fiml.core.logging import get_logger
from fiml.sessions.db import SessionMetrics
from fiml.sessions.models import Session

logger = get_logger(__name__)


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
    ) -> Dict[str, any]:
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
                # Build query
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                query = select(SessionMetrics).where(SessionMetrics.created_at >= cutoff_date)

                if user_id:
                    query = query.where(SessionMetrics.user_id == user_id)
                if session_type:
                    query = query.where(SessionMetrics.session_type == session_type)

                result = await db_session.execute(query)
                metrics = result.scalars().all()

                if not metrics:
                    return {
                        "total_sessions": 0,
                        "period_days": days,
                        "user_id": user_id,
                        "session_type": session_type,
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

                return {
                    "total_sessions": total_sessions,
                    "total_queries": total_queries,
                    "avg_duration_seconds": round(avg_duration, 2),
                    "avg_queries_per_session": round(avg_queries, 2),
                    "abandonment_rate": round(abandonment_rate, 4),
                    "period_days": days,
                    "user_id": user_id,
                    "session_type": session_type,
                    "top_assets": [{"symbol": symbol, "count": count} for symbol, count in top_assets],
                    "query_type_distribution": all_query_types,
                }

        except Exception as e:
            logger.error(f"Failed to get session stats: {e}")
            raise

    async def get_user_session_summary(self, user_id: str, days: int = 30) -> Dict[str, any]:
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
                cutoff_date = datetime.utcnow() - timedelta(days=days)
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
    ) -> Dict[str, any]:
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
