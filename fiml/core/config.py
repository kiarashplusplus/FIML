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
    fiml_env: Literal["development", "staging", "production"] = "development"
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

    # Security
    secret_key: str = "your-secret-key-change-in-production"
    api_key_header: str = "X-FIML-API-Key"
    enable_cors: bool = True
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])

    # Task Settings
    async_task_timeout: int = 300  # 5 minutes
    max_concurrent_tasks: int = 100
    task_result_ttl: int = 3600  # 1 hour

    @field_validator("fiml_env")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        if v not in ["development", "staging", "production"]:
            raise ValueError("fiml_env must be development, staging, or production")
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
