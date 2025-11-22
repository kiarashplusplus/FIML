"""
Core domain models and types
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class AssetType(str, Enum):
    """Asset type enumeration"""

    EQUITY = "equity"
    CRYPTO = "crypto"
    FOREX = "forex"
    COMMODITY = "commodity"
    INDEX = "index"
    ETF = "etf"
    OPTION = "option"
    FUTURE = "future"


class Market(str, Enum):
    """Market enumeration"""

    US = "US"
    UK = "UK"
    EU = "EU"
    JP = "JP"
    CN = "CN"
    HK = "HK"
    CRYPTO = "CRYPTO"
    GLOBAL = "GLOBAL"


class DataType(str, Enum):
    """Data type enumeration"""

    PRICE = "price"
    OHLCV = "ohlcv"
    FUNDAMENTALS = "fundamentals"
    TECHNICAL = "technical"
    SENTIMENT = "sentiment"
    NEWS = "news"
    MACRO = "macro"
    CORRELATION = "correlation"
    RISK = "risk"


class AnalysisDepth(str, Enum):
    """Analysis depth levels"""

    QUICK = "quick"  # Cached only
    STANDARD = "standard"  # Cached + fundamentals
    DEEP = "deep"  # Full analysis


class TaskStatus(str, Enum):
    """Task execution status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Asset(BaseModel):
    """Asset representation"""

    symbol: str
    name: Optional[str] = None
    asset_type: AssetType
    market: Market = Market.US  # Default to US market
    exchange: Optional[str] = None
    currency: str = "USD"

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().strip()


class ProviderScore(BaseModel):
    """Provider scoring metrics"""

    total: float = Field(ge=0, le=100)
    freshness: float = Field(ge=0, le=100)
    latency: float = Field(ge=0, le=100)
    uptime: float = Field(ge=0, le=100)
    completeness: float = Field(ge=0, le=100)
    reliability: float = Field(ge=0, le=100)


class DataLineage(BaseModel):
    """Data lineage and provenance"""

    providers: List[str]
    arbitration_score: float
    conflict_resolved: bool = False
    source_count: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CachedData(BaseModel):
    """Cached data response"""

    price: float
    change: float
    change_percent: float
    as_of: datetime
    last_updated: datetime
    source: str
    ttl: int  # seconds until refresh
    confidence: float = Field(ge=0, le=1)


class StructuralData(BaseModel):
    """Structural/fundamental data"""

    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    beta: Optional[float] = None
    avg_volume: Optional[float] = None
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None
    sector: Optional[str] = None
    industry: Optional[str] = None


class TaskInfo(BaseModel):
    """Async task information"""

    id: str
    type: str
    status: TaskStatus
    resource_url: str
    estimated_completion: Optional[datetime] = None
    progress: Optional[float] = Field(None, ge=0, le=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ComplianceInfo(BaseModel):
    """Compliance and disclaimer information"""

    region: str
    disclaimer: str
    restricted: bool = False
    warning_level: Literal["none", "low", "medium", "high"] = "none"
    applicable_regulations: List[str] = Field(default_factory=list)


class NarrativeSummary(BaseModel):
    """Narrative analysis summary"""

    summary: str
    key_insights: List[str]
    risk_factors: List[str]
    macro_context: Optional[str] = None
    technical_context: Optional[str] = None
    language: str = "en"


class SearchBySymbolResponse(BaseModel):
    """Response for search-by-symbol MCP tool"""

    symbol: str
    name: str
    exchange: str
    market: str
    currency: str
    cached: CachedData
    structural_data: Optional[StructuralData] = None
    task: TaskInfo
    disclaimer: str
    data_lineage: DataLineage


class SearchByCoinResponse(BaseModel):
    """Response for search-by-coin MCP tool"""

    symbol: str
    name: str
    pair: str
    exchange: str
    cached: CachedData
    crypto_metrics: Dict[str, Any] = Field(default_factory=dict)
    task: TaskInfo
    disclaimer: str
    data_lineage: DataLineage


class ArbitrationPlan(BaseModel):
    """Data arbitration execution plan"""

    primary_provider: str
    fallback_providers: List[str]
    merge_strategy: Optional[str] = None
    estimated_latency_ms: int
    timeout_ms: int = 5000

    @property
    def providers(self) -> List[str]:
        """Get all providers in the plan (primary + fallbacks)"""
        return [self.primary_provider] + self.fallback_providers


class ProviderHealth(BaseModel):
    """Provider health metrics"""

    provider_name: str
    is_healthy: bool
    uptime_percent: float
    avg_latency_ms: float
    success_rate: float
    last_check: datetime
    error_count_24h: int = 0
