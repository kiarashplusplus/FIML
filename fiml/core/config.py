"""
Core configuration using Pydantic Settings
"""

from functools import lru_cache
from typing import List, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """FIML Application Settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server Configuration
    fiml_env: Literal["development", "staging", "production", "test"] = "development"
    fiml_host: str = "0.0.0.0"
    fiml_port: int = 8000
    fiml_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    fiml_workers: int = 4

    # Redis Configuration (L1 Cache)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None
    redis_max_connections: int = 50
    redis_socket_timeout: int = 5

    # PostgreSQL Configuration (L2 Cache)
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "fiml"
    postgres_user: str = "fiml"
    postgres_password: str = "fiml_password"
    postgres_pool_size: int = 20
    postgres_max_overflow: int = 10

    # Celery Configuration
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_task_track_started: bool = True
    celery_task_time_limit: int = 300  # 5 minutes

    # Ray Configuration
    ray_address: str = "auto"
    ray_namespace: str = "fiml"

    # Kafka Configuration
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_prefix: str = "fiml"

    # Data Provider API Keys
    alpha_vantage_api_key: str | None = None
    fmp_api_key: str | None = None
    polygon_api_key: str | None = None
    finnhub_api_key: str | None = None
    newsapi_api_key: str | None = None
    newsapi_key: str | None = None  # Alternative name for NewsAPI key

    # NewsAPI Provider Settings
    newsapi_rate_limit_per_minute: int = 20  # Conservative for free tier
    newsapi_daily_limit: int = 100  # Free tier default (can be 1000 for paid)
    newsapi_enabled: bool = True

    # Azure OpenAI Configuration
    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_deployment_name: str | None = None
    azure_openai_api_version: str = "2024-02-15-preview"

    # Crypto Exchange Keys
    binance_api_key: str | None = None
    binance_secret_key: str | None = None
    coinbase_api_key: str | None = None
    coinbase_secret_key: str | None = None

    # Monitoring
    sentry_dsn: str | None = None
    prometheus_port: int = 9090
    grafana_port: int = 3000

    # Compliance & Regional Settings
    default_region: str = "US"
    enable_compliance_checks: bool = True
    enable_rate_limiting: bool = True
    max_requests_per_minute: int = 60
    allowed_regions: List[str] = Field(
        default_factory=lambda: ["US", "EU", "UK", "JP", "CA", "AU"]
    )

    # Feature Flags
    enable_crypto: bool = True
    enable_international_markets: bool = True
    enable_derivatives: bool = False
    enable_predictive_cache: bool = True
    enable_real_time_events: bool = True
    enable_cache_warming: bool = True
    enable_cache_eviction: bool = True

    # MCP Protocol
    mcp_protocol: Literal["stdio", "sse", "websocket"] = "stdio"
    mcp_enable_sse: bool = True
    mcp_enable_websocket: bool = True

    # Cache TTL Settings (in seconds)
    cache_ttl_price: int = 10  # 10 seconds for price data
    cache_ttl_fundamentals: int = 3600  # 1 hour
    cache_ttl_technical: int = 300  # 5 minutes
    cache_ttl_news: int = 600  # 10 minutes
    cache_ttl_macro: int = 86400  # 24 hours

    # Cache Optimization Settings
    cache_warming_enabled: bool = True
    cache_warming_interval_seconds: int = 300  # 5 minutes
    cache_eviction_policy: Literal["lru", "lfu", "ttl", "fifo"] = "lru"
    cache_max_tracked_entries: int = 10000
    cache_memory_pressure_threshold: float = 0.9  # 90%

    # Security
    secret_key: str = "your-secret-key-change-in-production"
    api_key_header: str = "X-FIML-API-Key"
    enable_cors: bool = True
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])

    # Task Settings
    async_task_timeout: int = 300  # 5 minutes
    max_concurrent_tasks: int = 100
    task_result_ttl: int = 3600  # 1 hour

    # Session Management Settings
    session_default_ttl_hours: int = 24  # 24 hours default session lifetime
    session_max_ttl_hours: int = 168  # 7 days maximum session lifetime
    session_cleanup_interval_minutes: int = 60  # Run cleanup every hour
    session_retention_days: int = 30  # Keep archived sessions for 30 days
    session_max_queries_per_session: int = 1000  # Max queries per session
    session_enable_analytics: bool = True  # Track session analytics

    # Worker Configuration for Production
    worker_pool_size: int = 8  # Number of worker instances per type
    worker_max_concurrent_tasks: int = 50  # Max concurrent tasks per worker
    worker_task_timeout: int = 120  # Task timeout in seconds (2 minutes)
    worker_retry_attempts: int = 3  # Number of retry attempts for failed tasks
    worker_retry_delay: int = 5  # Delay between retries in seconds
    worker_health_check_interval: int = 60  # Health check interval in seconds
    worker_memory_limit_mb: int = 2048  # Memory limit per worker in MB
    worker_cpu_limit: float = 2.0  # CPU cores limit per worker

    # Individual Worker Enable/Disable Flags
    enable_fundamentals_worker: bool = True
    enable_technical_worker: bool = True
    enable_macro_worker: bool = True
    enable_sentiment_worker: bool = True
    enable_correlation_worker: bool = True
    enable_risk_worker: bool = True
    enable_news_worker: bool = True
    enable_options_worker: bool = True

    # Watchdog Configuration for Production
    watchdog_global_enabled: bool = True  # Master switch for all watchdogs
    watchdog_event_stream_enabled: bool = True  # Enable event streaming
    watchdog_event_persistence: bool = True  # Persist events to Redis
    watchdog_websocket_broadcast: bool = True  # Broadcast events via WebSocket
    watchdog_max_events_in_memory: int = 1000  # Max events in circular buffer
    watchdog_health_check_interval: int = 60  # Health check interval in seconds

    # Individual Watchdog Enable/Disable Flags
    enable_earnings_anomaly_watchdog: bool = True
    enable_unusual_volume_watchdog: bool = True
    enable_whale_movement_watchdog: bool = True
    enable_funding_rate_watchdog: bool = True
    enable_liquidity_drop_watchdog: bool = True
    enable_correlation_breakdown_watchdog: bool = True
    enable_exchange_outage_watchdog: bool = True
    enable_price_anomaly_watchdog: bool = True

    # Watchdog Check Intervals (in seconds)
    earnings_anomaly_check_interval: int = 300  # 5 minutes
    unusual_volume_check_interval: int = 60  # 1 minute
    whale_movement_check_interval: int = 120  # 2 minutes
    funding_rate_check_interval: int = 300  # 5 minutes
    liquidity_drop_check_interval: int = 180  # 3 minutes
    correlation_breakdown_check_interval: int = 600  # 10 minutes
    exchange_outage_check_interval: int = 60  # 1 minute
    price_anomaly_check_interval: int = 30  # 30 seconds

    # Watchdog Alert Thresholds
    earnings_surprise_threshold_pct: float = 10.0  # Earnings surprise threshold percentage
    unusual_volume_multiplier: float = 3.0  # Volume spike threshold (3x average)
    whale_movement_min_usd: float = 1000000.0  # Minimum whale transfer amount in USD
    funding_rate_threshold_pct: float = 0.1  # Funding rate threshold percentage
    liquidity_drop_threshold_pct: float = 50.0  # Liquidity drop threshold percentage
    correlation_change_threshold: float = 0.5  # Correlation change threshold
    price_anomaly_threshold_pct: float = 5.0  # Price movement threshold percentage

    @field_validator("fiml_env")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        if v not in ["development", "staging", "production", "test"]:
            raise ValueError("fiml_env must be development, staging, production, or test")
        return v

    @property
    def database_url(self) -> str:
        """Construct PostgreSQL database URL"""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        """Construct Redis URL"""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.fiml_env == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.fiml_env == "production"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
