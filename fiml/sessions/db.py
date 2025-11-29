"""
SQLAlchemy models for session persistence in PostgreSQL
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for SQLAlchemy models"""

    pass


class SessionRecord(Base):
    """
    Archived session record in PostgreSQL

    Active sessions are in Redis, archived sessions are in PostgreSQL
    """

    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(String(255), index=True, nullable=True)
    type = Column(String(50), nullable=False, index=True)
    assets = Column(JSON, nullable=False, default=list)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True
    )
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    last_accessed_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    archived_at = Column(DateTime(timezone=True), nullable=True, index=True)
    is_archived = Column(Boolean, nullable=False, default=False, index=True)
    tags = Column(JSON, nullable=False, default=list)

    # Session state stored as JSON
    context = Column(JSON, nullable=False, default=dict)
    preferences = Column(JSON, nullable=False, default=dict)
    intermediate_results = Column(JSON, nullable=False, default=dict)
    session_metadata = Column(JSON, nullable=False, default=dict)

    # Analysis history stored as JSON
    history_queries = Column(JSON, nullable=False, default=list)
    total_queries = Column(Integer, nullable=False, default=0)
    first_query_at = Column(DateTime(timezone=True), nullable=True)
    last_query_at = Column(DateTime(timezone=True), nullable=True)
    cache_hit_rate = Column(String(50), nullable=False, default="0.0")

    metrics = relationship("SessionMetrics", backref="session", lazy="selectin")

    def __repr__(self) -> str:
        return f"<SessionRecord(id={self.id}, type={self.type}, user_id={self.user_id})>"


class SessionMetrics(Base):
    """
    Session analytics and metrics

    Aggregated metrics for session analysis
    """

    __tablename__ = "session_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(String(255), index=True, nullable=True)
    session_type = Column(String(50), nullable=False, index=True)

    # Timing metrics
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    duration_seconds = Column(Integer, nullable=False)

    # Query metrics
    total_queries = Column(Integer, nullable=False, default=0)
    cache_hit_rate = Column(String(50), nullable=False, default="0.0")
    avg_query_time_ms = Column(String(50), nullable=True)

    # Asset metrics
    assets_analyzed = Column(JSON, nullable=False, default=list)
    query_type_summary = Column(JSON, nullable=False, default=dict)

    # Session outcome
    completed_normally = Column(Boolean, nullable=False, default=False)
    abandoned = Column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        return f"<SessionMetrics(session_id={self.session_id}, queries={self.total_queries})>"


# Create tables SQL (for reference)
CREATE_TABLES_SQL = """
-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255),
    type VARCHAR(50) NOT NULL,
    assets JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    last_accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archived_at TIMESTAMPTZ,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    tags JSONB NOT NULL DEFAULT '[]',
    context JSONB NOT NULL DEFAULT '{}',
    preferences JSONB NOT NULL DEFAULT '{}',
    intermediate_results JSONB NOT NULL DEFAULT '{}',
    session_metadata JSONB NOT NULL DEFAULT '{}',
    history_queries JSONB NOT NULL DEFAULT '[]',
    total_queries INTEGER NOT NULL DEFAULT 0,
    first_query_at TIMESTAMPTZ,
    last_query_at TIMESTAMPTZ,
    cache_hit_rate VARCHAR(50) NOT NULL DEFAULT '0.0'
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_type ON sessions(type);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_sessions_archived ON sessions(is_archived);
CREATE INDEX IF NOT EXISTS idx_sessions_archived_at ON sessions(archived_at);

-- Session metrics table
CREATE TABLE IF NOT EXISTS session_metrics (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    user_id VARCHAR(255),
    session_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    duration_seconds INTEGER NOT NULL,
    total_queries INTEGER NOT NULL DEFAULT 0,
    cache_hit_rate VARCHAR(50) NOT NULL DEFAULT '0.0',
    avg_query_time_ms VARCHAR(50),
    assets_analyzed JSONB NOT NULL DEFAULT '[]',
    query_type_summary JSONB NOT NULL DEFAULT '{}',
    completed_normally BOOLEAN NOT NULL DEFAULT FALSE,
    abandoned BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_session_metrics_session_id ON session_metrics(session_id);
CREATE INDEX IF NOT EXISTS idx_session_metrics_user_id ON session_metrics(user_id);
CREATE INDEX IF NOT EXISTS idx_session_metrics_type ON session_metrics(session_type);
CREATE INDEX IF NOT EXISTS idx_session_metrics_created_at ON session_metrics(created_at);

-- Cleanup expired sessions (retention policy)
CREATE INDEX IF NOT EXISTS idx_sessions_cleanup ON sessions(is_archived, expires_at)
    WHERE is_archived = FALSE;
"""
