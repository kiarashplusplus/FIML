"""
Session store with Redis (active) and PostgreSQL (archived) backends
"""

import json
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional, cast
from uuid import UUID

import redis.asyncio as redis
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from fiml.core import config
from fiml.core.exceptions import CacheError
from fiml.core.logging import get_logger
from fiml.sessions.db import SessionMetrics, SessionRecord
from fiml.sessions.models import AnalysisHistory, QueryRecord, Session, SessionSummary, SessionType

logger = get_logger(__name__)


class SessionStore:
    """
    Session storage with Redis for active sessions and PostgreSQL for archives

    Architecture:
    - Active sessions (TTL < 24h): Redis
    - Archived sessions: PostgreSQL
    - Auto-archival on expiration
    - Session cleanup background task
    """

    def __init__(self) -> None:
        self._redis: Optional[redis.Redis] = None
        self._engine: Optional[AsyncEngine] = None
        self._session_maker: Optional[async_sessionmaker[AsyncSession]] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize Redis and PostgreSQL connections"""
        if self._initialized:
            logger.warning("SessionStore already initialized")
            return

        try:
            # Initialize Redis for active sessions
            print(f"DEBUG: SessionStore initializing with Redis port: {config.settings.redis_port}, Postgres port: {config.settings.postgres_port}")
            self._redis = redis.Redis(
                host=config.settings.redis_host,
                port=config.settings.redis_port,
                db=config.settings.redis_db,
                password=config.settings.redis_password,
                decode_responses=True,
                max_connections=config.settings.redis_max_connections,
                socket_timeout=config.settings.redis_socket_timeout,
            )

            # Test Redis connection
            ping_result = await self._redis.ping()
            if not ping_result:
                raise CacheError("Redis ping failed")

            # Initialize PostgreSQL for archived sessions
            self._engine = create_async_engine(
                config.settings.database_url,
                pool_size=config.settings.postgres_pool_size,
                max_overflow=config.settings.postgres_max_overflow,
                echo=config.settings.is_development,
            )

            self._session_maker = async_sessionmaker(
                self._engine,
                expire_on_commit=False,
            )

            # Test PostgreSQL connection
            async with self._engine.begin() as conn:
                await conn.execute(text("SELECT 1"))

            self._initialized = True
            logger.info("SessionStore initialized (Redis + PostgreSQL)")

        except Exception as e:
            logger.error(f"Failed to initialize SessionStore: {e}")
            raise CacheError(f"SessionStore initialization failed: {e}")

    async def shutdown(self) -> None:
        """Close all connections"""
        if self._redis:
            await self._redis.close()
        if self._engine:
            await self._engine.dispose()
        self._initialized = False
        logger.info("SessionStore shutdown")

    def _session_key(self, session_id: UUID) -> str:
        """Generate Redis key for session"""
        return f"session:{session_id}"

    async def create_session(
        self,
        assets: List[str],
        session_type: SessionType,
        user_id: Optional[str] = None,
        ttl_hours: int = 24,
        tags: Optional[List[str]] = None,
    ) -> Session:
        """
        Create a new analysis session

        Args:
            assets: List of asset symbols
            session_type: Type of analysis
            user_id: Optional user identifier
            ttl_hours: Time to live in hours
            tags: Optional tags for categorization

        Returns:
            Created session
        """
        if not self._initialized or not self._redis:
            raise CacheError("SessionStore not initialized")

        try:
            # Create session object
            session = Session(
                user_id=user_id,
                type=session_type,
                assets=assets,
                expires_at=datetime.now(UTC) + timedelta(hours=ttl_hours),
                tags=tags or [],
            )

            # Store in Redis
            key = self._session_key(session.id)
            session_data = json.dumps(session.to_dict())
            ttl_seconds = ttl_hours * 3600

            await self._redis.setex(key, ttl_seconds, session_data)

            logger.info(
                f"Created session {session.id}",
                session_type=session_type.value,
                assets=assets,
                ttl_hours=ttl_hours,
            )

            return session

        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise CacheError(f"Session creation failed: {e}")

    async def get_session(self, session_id: UUID) -> Optional[Session]:
        """
        Get session by ID

        First checks Redis (active), then PostgreSQL (archived)

        Args:
            session_id: Session UUID

        Returns:
            Session if found, None otherwise
        """
        if not self._initialized or not self._redis:
            raise CacheError("SessionStore not initialized")

        try:
            # Try Redis first (active sessions)
            key = self._session_key(session_id)
            session_data = await self._redis.get(key)

            if session_data:
                session = Session.from_dict(json.loads(session_data))
                session.touch()  # Update last accessed
                await self._update_redis_session(session)
                return session

            # Fall back to PostgreSQL (archived sessions)
            if self._session_maker:
                async with self._session_maker() as db_session:
                    result = await db_session.execute(
                        select(SessionRecord).where(SessionRecord.id == session_id)
                    )
                    record = result.scalar_one_or_none()

                    if record:
                        return self._session_from_record(record)

            logger.debug(f"Session {session_id} not found")
            return None

        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            raise CacheError(f"Session retrieval failed: {e}")

    async def update_session(self, session_id: UUID, session: Session) -> None:
        """
        Update session state

        Args:
            session_id: Session UUID
            session: Updated session object
        """
        if not self._initialized or not self._redis:
            raise CacheError("SessionStore not initialized")

        try:
            session.touch()
            await self._update_redis_session(session)

            logger.debug(f"Updated session {session_id}")

        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {e}")
            raise CacheError(f"Session update failed: {e}")

    async def _update_redis_session(self, session: Session) -> None:
        """Update session in Redis"""
        if not self._redis:
            return

        key = self._session_key(session.id)
        session_data = json.dumps(session.to_dict())

        # Calculate remaining TTL
        ttl_seconds = int(session.time_remaining.total_seconds())
        if ttl_seconds > 0:
            await self._redis.setex(key, ttl_seconds, session_data)

    async def delete_session(self, session_id: UUID) -> bool:
        """
        Delete session

        Args:
            session_id: Session UUID

        Returns:
            True if deleted, False if not found
        """
        if not self._initialized or not self._redis:
            raise CacheError("SessionStore not initialized")

        try:
            key = self._session_key(session_id)
            result = await self._redis.delete(key)

            if result:
                logger.info(f"Deleted session {session_id}")
                return True

            logger.debug(f"Session {session_id} not found for deletion")
            return False

        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            raise CacheError(f"Session deletion failed: {e}")

    async def list_user_sessions(
        self,
        user_id: str,
        include_archived: bool = False,
        limit: int = 100,
    ) -> List[SessionSummary]:
        """
        List all sessions for a user

        Args:
            user_id: User identifier
            include_archived: Include archived sessions
            limit: Maximum number of sessions to return

        Returns:
            List of session summaries
        """
        if not self._initialized or not self._redis:
            raise CacheError("SessionStore not initialized")

        summaries: List[SessionSummary] = []

        try:
            # Get active sessions from Redis
            pattern = "session:*"
            cursor = 0
            count = 0

            while True:
                cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)

                for key in keys:
                    if count >= limit:
                        break

                    session_data = await self._redis.get(key)
                    if session_data:
                        session = Session.from_dict(json.loads(session_data))
                        if session.user_id == user_id:
                            summaries.append(SessionSummary.from_session(session))
                            count += 1

                if cursor == 0 or count >= limit:
                    break

            # Get archived sessions from PostgreSQL
            if include_archived and self._session_maker and count < limit:
                async with self._session_maker() as db_session:
                    result = await db_session.execute(
                        select(SessionRecord)
                        .where(SessionRecord.user_id == user_id)
                        .where(SessionRecord.is_archived)
                        .order_by(SessionRecord.archived_at.desc())
                        .limit(limit - count)
                    )
                    records = result.scalars().all()

                    for record in records:
                        session = self._session_from_record(record)
                        summaries.append(SessionSummary.from_session(session))

            logger.debug(f"Found {len(summaries)} sessions for user {user_id}")
            return summaries

        except Exception as e:
            logger.error(f"Failed to list sessions for user {user_id}: {e}")
            raise CacheError(f"Session listing failed: {e}")

    async def extend_session(self, session_id: UUID, hours: int = 24) -> None:
        """
        Extend session expiration

        Args:
            session_id: Session UUID
            hours: Hours to extend by
        """
        session = await self.get_session(session_id)
        if session:
            session.extend(hours)
            await self.update_session(session_id, session)
            logger.info(f"Extended session {session_id} by {hours} hours")

    async def archive_session(self, session_id: UUID) -> bool:
        """
        Archive session from Redis to PostgreSQL

        Args:
            session_id: Session UUID

        Returns:
            True if archived, False if not found
        """
        if not self._initialized or not self._session_maker:
            raise CacheError("SessionStore not initialized")

        try:
            # Get session from Redis
            session = await self.get_session(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found for archival")
                return False

            # Create PostgreSQL record
            async with self._session_maker() as db_session:
                record = self._record_from_session(session)
                record.is_archived = True  # type: ignore
                record.archived_at = datetime.now(UTC)  # type: ignore

                db_session.add(record)
                await db_session.commit()

            # Remove from Redis
            await self.delete_session(session_id)

            logger.info(f"Archived session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to archive session {session_id}: {e}")
            raise CacheError(f"Session archival failed: {e}")

    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions

        Archives expired sessions to PostgreSQL and removes from Redis

        Returns:
            Number of sessions cleaned up
        """
        if not self._initialized or not self._redis:
            raise CacheError("SessionStore not initialized")

        cleaned_count = 0

        try:
            pattern = "session:*"
            cursor = 0

            while True:
                cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)

                for key in keys:
                    session_data = await self._redis.get(key)
                    if session_data:
                        session = Session.from_dict(json.loads(session_data))

                        if session.is_expired:
                            # Archive to PostgreSQL
                            await self.archive_session(session.id)
                            cleaned_count += 1

                if cursor == 0:
                    break

            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired sessions")

            return cleaned_count

        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            raise CacheError(f"Session cleanup failed: {e}")

    def _record_from_session(self, session: Session) -> SessionRecord:
        """Convert Session to SessionRecord"""
        return SessionRecord(
            id=session.id,
            user_id=session.user_id,
            type=session.type.value,
            assets=session.assets,
            created_at=session.created_at,
            expires_at=session.expires_at,
            last_accessed_at=session.last_accessed_at,
            is_archived=session.is_archived,
            tags=session.tags,
            context=session.state.context,
            preferences=session.state.preferences,
            intermediate_results=session.state.intermediate_results,
            session_metadata=session.state.metadata,
            history_queries=[q.model_dump(mode="json") for q in session.state.history.queries],
            total_queries=session.state.history.total_queries,
            first_query_at=session.state.history.first_query_at,
            last_query_at=session.state.history.last_query_at,
            cache_hit_rate=str(session.state.history.cache_hit_rate),
        )

    def _session_from_record(self, record: SessionRecord) -> Session:
        """Convert SessionRecord to Session"""
        # Reconstruct history
        queries = [QueryRecord(**q) for q in getattr(record, "history_queries", [])]
        history = AnalysisHistory(
            queries=queries,
            total_queries=cast(int, record.total_queries),
            first_query_at=cast(Optional[datetime], record.first_query_at),
            last_query_at=cast(Optional[datetime], record.last_query_at),
            cache_hit_rate=float(cast(float, record.cache_hit_rate)),
        )

        from fiml.sessions.models import SessionState

        state = SessionState(
            context=cast(Dict[str, Any], record.context),
            preferences=cast(Dict[str, Any], record.preferences),
            intermediate_results=cast(Dict[str, Any], record.intermediate_results),
            metadata=cast(Dict[str, Any], record.session_metadata),
            history=history,
        )

        # Reconstruct metrics if available
        metrics_list: List[SessionMetrics] = getattr(record, "metrics", [])
        for m in metrics_list:
            # Add metrics to history if needed
            pass
        return Session(
            id=record.id,
            user_id=record.user_id,
            type=SessionType(record.type),
            assets=record.assets,
            created_at=record.created_at,
            expires_at=record.expires_at,
            last_accessed_at=record.last_accessed_at,
            state=state,
            is_archived=record.is_archived,
            tags=record.tags,
        )


# Global session store instance
_session_store: Optional[SessionStore] = None


async def get_session_store() -> SessionStore:
    """Get or create global session store instance"""
    global _session_store

    if _session_store is None:
        _session_store = SessionStore()
        await _session_store.initialize()

    return _session_store
