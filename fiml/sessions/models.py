"""
Session data models for FIML analysis workflows
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class SessionType(str, Enum):
    """Type of analysis session"""

    EQUITY = "equity"
    CRYPTO = "crypto"
    PORTFOLIO = "portfolio"
    COMPARATIVE = "comparative"
    MACRO = "macro"


class QueryRecord(BaseModel):
    """Individual query in session history"""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    query_type: str  # e.g., "price", "fundamentals", "technical"
    parameters: Dict[str, Any] = Field(default_factory=dict)
    result_summary: Optional[str] = None
    execution_time_ms: Optional[float] = None
    cache_hit: bool = False


class AnalysisHistory(BaseModel):
    """Complete analysis history for a session"""

    queries: List[QueryRecord] = Field(default_factory=list)
    total_queries: int = 0
    first_query_at: Optional[datetime] = None
    last_query_at: Optional[datetime] = None
    cache_hit_rate: float = 0.0

    def add_query(self, query: QueryRecord) -> None:
        """Add a query to the history"""
        self.queries.append(query)
        self.total_queries += 1
        self.last_query_at = query.timestamp

        if self.first_query_at is None:
            self.first_query_at = query.timestamp

        # Update cache hit rate
        total_hits = sum(1 for q in self.queries if q.cache_hit)
        self.cache_hit_rate = total_hits / self.total_queries if self.total_queries > 0 else 0.0

    def get_recent_queries(self, limit: int = 10) -> List[QueryRecord]:
        """Get most recent queries"""
        return self.queries[-limit:]

    def get_query_types_summary(self) -> Dict[str, int]:
        """Get count of queries by type"""
        summary: Dict[str, int] = {}
        for query in self.queries:
            summary[query.query_type] = summary.get(query.query_type, 0) + 1
        return summary


class SessionState(BaseModel):
    """Current state and context of a session"""

    context: Dict[str, Any] = Field(default_factory=dict)  # User-defined context
    history: AnalysisHistory = Field(default_factory=AnalysisHistory)
    preferences: Dict[str, Any] = Field(default_factory=dict)  # User preferences
    intermediate_results: Dict[str, Any] = Field(default_factory=dict)  # Cached analysis results
    metadata: Dict[str, Any] = Field(default_factory=dict)  # Additional metadata

    def update_context(self, key: str, value: Any) -> None:
        """Update session context"""
        self.context[key] = value
        self.metadata["last_updated"] = datetime.utcnow().isoformat()

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context value"""
        return self.context.get(key, default)

    def store_intermediate_result(self, key: str, result: Any) -> None:
        """Store intermediate analysis result"""
        self.intermediate_results[key] = {
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def get_intermediate_result(self, key: str) -> Optional[Any]:
        """Get intermediate result if exists"""
        data = self.intermediate_results.get(key)
        return data["result"] if data else None


class Session(BaseModel):
    """Analysis session model"""

    id: UUID = Field(default_factory=uuid4)
    user_id: Optional[str] = None
    type: SessionType
    assets: List[str] = Field(default_factory=list)  # Symbols being analyzed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    last_accessed_at: datetime = Field(default_factory=datetime.utcnow)
    state: SessionState = Field(default_factory=SessionState)
    is_archived: bool = False
    tags: List[str] = Field(default_factory=list)  # User-defined tags

    def __init__(self, **data):
        # Set default expiration if not provided
        if "expires_at" not in data:
            data["expires_at"] = datetime.utcnow() + timedelta(hours=24)
        super().__init__(**data)

    @property
    def is_expired(self) -> bool:
        """Check if session has expired"""
        return datetime.utcnow() > self.expires_at

    @property
    def time_remaining(self) -> timedelta:
        """Get time remaining before expiration"""
        return self.expires_at - datetime.utcnow()

    @property
    def duration(self) -> timedelta:
        """Get total session duration so far"""
        return self.last_accessed_at - self.created_at

    def extend(self, hours: int = 24) -> None:
        """Extend session expiration"""
        self.expires_at = datetime.utcnow() + timedelta(hours=hours)

    def touch(self) -> None:
        """Update last accessed timestamp"""
        self.last_accessed_at = datetime.utcnow()

    def add_query(self, query: QueryRecord) -> None:
        """Add a query to the session history"""
        self.state.history.add_query(query)
        self.touch()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "type": self.type.value,
            "assets": self.assets,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "last_accessed_at": self.last_accessed_at.isoformat(),
            "state": self.state.model_dump(),
            "is_archived": self.is_archived,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """Create from dictionary"""
        # Convert string dates back to datetime
        for field in ["created_at", "expires_at", "last_accessed_at"]:
            if isinstance(data.get(field), str):
                data[field] = datetime.fromisoformat(data[field])

        # Convert string UUID to UUID
        if isinstance(data.get("id"), str):
            data["id"] = UUID(data["id"])

        # Convert state dict to SessionState
        if isinstance(data.get("state"), dict):
            data["state"] = SessionState(**data["state"])

        return cls(**data)


class SessionSummary(BaseModel):
    """Summary of session for listing"""

    id: UUID
    user_id: Optional[str]
    type: SessionType
    assets: List[str]
    created_at: datetime
    expires_at: datetime
    total_queries: int
    is_expired: bool
    is_archived: bool
    tags: List[str]

    @classmethod
    def from_session(cls, session: Session) -> "SessionSummary":
        """Create summary from full session"""
        return cls(
            id=session.id,
            user_id=session.user_id,
            type=session.type,
            assets=session.assets,
            created_at=session.created_at,
            expires_at=session.expires_at,
            total_queries=session.state.history.total_queries,
            is_expired=session.is_expired,
            is_archived=session.is_archived,
            tags=session.tags,
        )
