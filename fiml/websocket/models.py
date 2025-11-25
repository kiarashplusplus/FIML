"""
WebSocket data models
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from fiml.core.models import AssetType, DataType, Market


class StreamType(str, Enum):
    """WebSocket stream types"""

    PRICE = "price"  # Real-time price updates
    OHLCV = "ohlcv"  # Candlestick updates
    QUOTE = "quote"  # Bid/ask quotes
    TRADES = "trades"  # Recent trades
    MULTI_ASSET = "multi_asset"  # Multiple assets at once


class MessageType(str, Enum):
    """WebSocket message types"""

    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    SUBSCRIPTION_ACK = "subscription_ack"
    SUBSCRIPTION_ERROR = "subscription_error"
    DATA = "data"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


class SubscriptionRequest(BaseModel):
    """Client subscription request"""

    type: MessageType = MessageType.SUBSCRIBE
    stream_type: StreamType
    symbols: List[str] = Field(min_length=1, max_length=50)
    asset_type: AssetType = AssetType.EQUITY
    market: Market = Market.US
    interval_ms: int = Field(default=1000, ge=100, le=60000)  # Update interval
    data_type: DataType = DataType.PRICE
    params: Dict[str, Any] = Field(default_factory=dict)


class UnsubscribeRequest(BaseModel):
    """Client unsubscribe request"""

    type: MessageType = MessageType.UNSUBSCRIBE
    stream_type: StreamType
    symbols: Optional[List[str]] = None  # If None, unsubscribe from all


class SubscriptionResponse(BaseModel):
    """Server subscription acknowledgment"""

    type: MessageType = MessageType.SUBSCRIPTION_ACK
    stream_type: StreamType
    symbols: List[str]
    subscription_id: str
    interval_ms: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    disclaimer: str = (
        "⚠️ DISCLAIMER: Real-time market data is for informational purposes only. "
        "This is not financial advice. Markets are volatile and data may be delayed. "
        "See LICENSE file for complete liability disclaimer."
    )


class WebSocketError(BaseModel):
    """WebSocket error message"""

    type: MessageType = MessageType.ERROR
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PriceUpdate(BaseModel):
    """Real-time price update"""

    symbol: str
    price: float
    change: float
    change_percent: float
    volume: Optional[float] = None
    timestamp: datetime
    provider: str
    confidence: float = Field(ge=0, le=1)


class OHLCVUpdate(BaseModel):
    """Real-time OHLCV candle update"""

    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    is_closed: bool = False  # Whether candle is finalized


class QuoteUpdate(BaseModel):
    """Real-time bid/ask quote update"""

    symbol: str
    bid: float
    ask: float
    bid_size: Optional[float] = None
    ask_size: Optional[float] = None
    spread: float
    timestamp: datetime


class TradeUpdate(BaseModel):
    """Recent trade update"""

    symbol: str
    price: float
    quantity: float
    timestamp: datetime
    trade_id: Optional[str] = None
    side: Optional[str] = None  # "buy" or "sell"


class StreamMessage(BaseModel):
    """Streaming data message"""

    type: MessageType = MessageType.DATA
    stream_type: StreamType
    subscription_id: str
    data: List[Any]  # List of PriceUpdate, OHLCVUpdate, QuoteUpdate, or TradeUpdate
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)
    disclaimer: Optional[str] = None  # Optional per-message disclaimer for important updates


class HeartbeatMessage(BaseModel):
    """Heartbeat/keepalive message"""

    type: MessageType = MessageType.HEARTBEAT
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    active_subscriptions: int = 0
