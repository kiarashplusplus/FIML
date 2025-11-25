"""
Specialized Watchdog Detectors

Implements 8 specialized watchdogs for detecting various market anomalies
and events in real-time.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import numpy as np

from fiml.core.logging import get_logger
from fiml.core.models import Asset, AssetType, DataType
from fiml.watchdog.base import BaseWatchdog
from fiml.watchdog.models import EventType, Severity, WatchdogEvent

logger = get_logger(__name__)


class EarningsAnomalyWatchdog(BaseWatchdog):
    """
    Monitors actual earnings vs estimates for significant beats/misses

    Detects:
    - Earnings surprises >10% deviation
    - Revenue surprises
    - Guidance changes
    """

    def __init__(self, check_interval: int = 300, **kwargs: Any):  # 5 minutes
        super().__init__(check_interval=check_interval, **kwargs)
        self._monitored_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        self._last_checked: Dict[str, datetime] = {}

    @property
    def name(self) -> str:
        return "earnings_anomaly"

    async def check(self) -> Optional[WatchdogEvent]:
        """Check for earnings anomalies"""

        for symbol in self._monitored_symbols:
            try:
                asset = Asset(symbol=symbol, asset_type=AssetType.EQUITY)

                # Get latest earnings data
                earnings_data = await self._get_earnings_data(asset)
                if not earnings_data:
                    continue

                # Check if we've already processed this earnings report
                report_date = earnings_data.get("report_date")
                if not report_date:
                    continue

                last_check = self._last_checked.get(symbol)
                if last_check and last_check >= report_date:
                    continue  # Already processed

                # Calculate surprise
                actual = earnings_data.get("actual_eps", 0)
                estimate = earnings_data.get("estimated_eps", 0)

                if estimate == 0:
                    continue

                surprise_pct = ((actual - estimate) / abs(estimate)) * 100

                # Detect significant beat/miss (>10%)
                if abs(surprise_pct) > 10:
                    self._last_checked[symbol] = report_date

                    severity = Severity.HIGH if abs(surprise_pct) > 20 else Severity.MEDIUM

                    return WatchdogEvent(
                        type=EventType.EARNINGS_ANOMALY,
                        severity=severity,
                        asset=asset,
                        description=f"{symbol} {'beat' if surprise_pct > 0 else 'missed'} "
                                  f"earnings by {abs(surprise_pct):.1f}%",
                        data={
                            "actual_eps": actual,
                            "estimated_eps": estimate,
                            "surprise_pct": surprise_pct,
                            "report_date": report_date.isoformat(),
                            "revenue": earnings_data.get("revenue"),
                            "revenue_estimate": earnings_data.get("revenue_estimate"),
                        },
                        watchdog=self.name,
                    )
            except Exception as e:
                logger.error(f"Error checking earnings for {symbol}: {e}")

        return None

    async def _get_earnings_data(self, asset: Asset) -> Optional[Dict]:
        """Get earnings data from providers"""
        # This would fetch from Alpha Vantage, FMP, or other provider
        # For now, return mock data
        return None


class UnusualVolumeWatchdog(BaseWatchdog):
    """
    Tracks volume vs 30-day average, alerts on >3x spikes

    Detects:
    - Volume spikes (>3x average)
    - Correlation with price movement
    - Sustained high volume
    """

    def __init__(self, check_interval: int = 60, **kwargs: Any):  # 1 minute
        super().__init__(check_interval=check_interval, **kwargs)
        self._monitored_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "SPY", "QQQ"]

    @property
    def name(self) -> str:
        return "unusual_volume"

    async def check(self) -> Optional[WatchdogEvent]:
        """Check for unusual volume"""
        from fiml.arbitration.engine import arbitration_engine

        for symbol in self._monitored_symbols:
            try:
                asset = Asset(symbol=symbol, asset_type=AssetType.EQUITY)

                # Get current price data via arbitration engine
                plan = await arbitration_engine.arbitrate_request(
                    asset=asset,
                    data_type=DataType.PRICE,
                )
                response = await arbitration_engine.execute_with_fallback(
                    plan=plan,
                    asset=asset,
                    data_type=DataType.PRICE,
                )

                if not response or not response.data or "volume" not in response.data:
                    continue

                current_data = response.data

                current_volume = current_data["volume"]

                # Get 30-day average volume from cache
                avg_volume = await self._get_avg_volume(asset, days=30)
                if not avg_volume or avg_volume == 0:
                    continue

                # Calculate volume ratio
                volume_ratio = current_volume / avg_volume

                # Alert on >3x volume spike
                if volume_ratio > 3.0:
                    # Get price change
                    price_change_pct = current_data.get("change_pct", 0)

                    severity = Severity.CRITICAL if volume_ratio > 5.0 else Severity.HIGH

                    return WatchdogEvent(
                        type=EventType.UNUSUAL_VOLUME,
                        severity=severity,
                        asset=asset,
                        description=f"{symbol} volume spike: {volume_ratio:.1f}x average",
                        data={
                            "current_volume": current_volume,
                            "avg_volume": avg_volume,
                            "volume_ratio": volume_ratio,
                            "price_change_pct": price_change_pct,
                            "price": current_data.get("price"),
                        },
                        watchdog=self.name,
                    )
            except Exception as e:
                logger.error(f"Error checking volume for {symbol}: {e}")

        return None

    async def _get_avg_volume(self, asset: Asset, days: int = 30) -> Optional[float]:
        """Get average volume from cache"""

        try:
            # Get historical data
            end_date = datetime.now(timezone.utc)
            end_date - timedelta(days=days)

            # This would fetch from cache
            # For now, return None to skip
            return None
        except Exception as e:
            logger.error(f"Error getting avg volume: {e}")
            return None


class WhaleMovementWatchdog(BaseWatchdog):
    """
    Monitors large crypto transfers (>$1M)

    Detects:
    - Large wallet transfers
    - Exchange inflows/outflows
    - Whale accumulation patterns
    """

    def __init__(self, check_interval: int = 120, **kwargs: Any):  # 2 minutes
        super().__init__(check_interval=check_interval, **kwargs)
        self._monitored_tokens = ["BTC", "ETH", "SOL", "USDT", "USDC"]
        self._threshold_usd = 1_000_000

    @property
    def name(self) -> str:
        return "whale_movement"

    async def check(self) -> Optional[WatchdogEvent]:
        """Check for whale movements"""
        # In production, this would monitor blockchain transactions
        # via APIs like Etherscan, Blockchain.com, or node connections

        # For now, return None (would need blockchain API integration)
        return None


class FundingRateWatchdog(BaseWatchdog):
    """
    Monitors perpetual futures funding rates

    Detects:
    - Extreme funding rates (>0.1% or <-0.1%)
    - Funding rate spikes
    - Sustained high/low funding
    """

    def __init__(self, check_interval: int = 300, **kwargs: Any):  # 5 minutes
        super().__init__(check_interval=check_interval, **kwargs)
        self._monitored_symbols = ["BTC", "ETH", "SOL"]
        self._exchanges = ["binance", "bybit", "okx"]

    @property
    def name(self) -> str:
        return "funding_rate"

    async def check(self) -> Optional[WatchdogEvent]:
        """Check for funding rate anomalies"""
        for symbol in self._monitored_symbols:
            try:
                asset = Asset(symbol=symbol, asset_type=AssetType.CRYPTO)

                # Get funding rates from exchanges
                funding_rates = await self._get_funding_rates(asset)
                if not funding_rates:
                    continue

                # Calculate average
                avg_funding = np.mean(list(funding_rates.values()))

                # Alert on extreme funding (>0.1% per 8h = 0.001)
                if abs(avg_funding) > 0.001:
                    severity = Severity.CRITICAL if abs(avg_funding) > 0.003 else Severity.HIGH

                    return WatchdogEvent(
                        type=EventType.FUNDING_SPIKE,
                        severity=severity,
                        asset=asset,
                        description=f"{symbol} extreme funding rate: "
                                  f"{avg_funding * 100:.3f}% per 8h",
                        data={
                            "avg_funding_rate": avg_funding,
                            "funding_rate_pct": avg_funding * 100,
                            "by_exchange": funding_rates,
                        },
                        watchdog=self.name,
                    )
            except Exception as e:
                logger.error(f"Error checking funding rate for {symbol}: {e}")

        return None

    async def _get_funding_rates(self, asset: Asset) -> Dict[str, float]:
        """Get funding rates from exchanges"""
        # In production, would fetch from exchange APIs
        # For now, return empty dict
        return {}


class LiquidityDropWatchdog(BaseWatchdog):
    """
    Tracks order book depth, alerts on >50% reduction

    Detects:
    - Liquidity drops
    - Bid-ask spread widening
    - Order book imbalances
    """

    def __init__(self, check_interval: int = 180, **kwargs: Any):  # 3 minutes
        super().__init__(check_interval=check_interval, **kwargs)
        self._monitored_symbols = ["BTC", "ETH", "SOL", "SPY", "QQQ"]

    @property
    def name(self) -> str:
        return "liquidity_drop"

    async def check(self) -> Optional[WatchdogEvent]:
        """Check for liquidity drops"""
        for symbol in self._monitored_symbols:
            try:
                # Determine asset type
                asset_type = AssetType.CRYPTO if symbol in ["BTC", "ETH", "SOL"] else AssetType.EQUITY
                asset = Asset(symbol=symbol, asset_type=asset_type)

                # Get current order book depth
                current_depth = await self._get_order_book_depth(asset)
                if not current_depth:
                    continue

                # Get 7-day average depth
                avg_depth = await self._get_avg_depth(asset, days=7)
                if not avg_depth or avg_depth == 0:
                    continue

                # Calculate drop
                depth_ratio = current_depth / avg_depth

                # Alert on >50% drop
                if depth_ratio < 0.5:
                    severity = Severity.CRITICAL if depth_ratio < 0.3 else Severity.HIGH

                    return WatchdogEvent(
                        type=EventType.LIQUIDITY_DROP,
                        severity=severity,
                        asset=asset,
                        description=f"{symbol} liquidity dropped {(1 - depth_ratio) * 100:.0f}%",
                        data={
                            "current_depth": current_depth,
                            "avg_depth": avg_depth,
                            "drop_pct": (1 - depth_ratio) * 100,
                            "depth_ratio": depth_ratio,
                        },
                        watchdog=self.name,
                    )
            except Exception as e:
                logger.error(f"Error checking liquidity for {symbol}: {e}")

        return None

    async def _get_order_book_depth(self, asset: Asset) -> Optional[float]:
        """Get current order book depth"""
        # Would fetch from exchange API
        return None

    async def _get_avg_depth(self, asset: Asset, days: int) -> Optional[float]:
        """Get average order book depth"""
        # Would fetch from historical data
        return None


class CorrelationBreakdownWatchdog(BaseWatchdog):
    """
    Tracks rolling correlations, detects changes >0.5

    Detects:
    - Correlation breakdowns
    - Regime changes
    - Decoupling events
    """

    def __init__(self, check_interval: int = 600, **kwargs: Any):  # 10 minutes
        super().__init__(check_interval=check_interval, **kwargs)
        self._correlation_pairs = [
            ("BTC", "ETH"),
            ("SPY", "QQQ"),
            ("GLD", "TLT"),
            ("BTC", "SPY"),
        ]

    @property
    def name(self) -> str:
        return "correlation_breakdown"

    async def check(self) -> Optional[WatchdogEvent]:
        """Check for correlation breakdowns"""
        for symbol1, symbol2 in self._correlation_pairs:
            try:
                asset1 = self._symbol_to_asset(symbol1)
                asset2 = self._symbol_to_asset(symbol2)

                # Calculate recent correlation (7 days)
                recent_corr = await self._calculate_correlation(asset1, asset2, window_days=7)
                if recent_corr is None:
                    continue

                # Calculate historical correlation (90 days)
                hist_corr = await self._calculate_correlation(asset1, asset2, window_days=90)
                if hist_corr is None:
                    continue

                # Detect breakdown
                corr_change = abs(recent_corr - hist_corr)

                if corr_change > 0.5:
                    severity = Severity.HIGH if corr_change > 0.7 else Severity.MEDIUM

                    return WatchdogEvent(
                        type=EventType.CORRELATION_BREAK,
                        severity=severity,
                        asset=asset1,
                        description=f"Correlation between {symbol1} and {symbol2} broke down",
                        data={
                            "asset1": symbol1,
                            "asset2": symbol2,
                            "recent_corr": recent_corr,
                            "hist_corr": hist_corr,
                            "change": corr_change,
                        },
                        watchdog=self.name,
                    )
            except Exception as e:
                logger.error(f"Error checking correlation for {symbol1}/{symbol2}: {e}")

        return None

    def _symbol_to_asset(self, symbol: str) -> Asset:
        """Convert symbol to asset"""
        if symbol in ["BTC", "ETH", "SOL"]:
            return Asset(symbol=symbol, asset_type=AssetType.CRYPTO)
        return Asset(symbol=symbol, asset_type=AssetType.EQUITY)

    async def _calculate_correlation(
        self,
        asset1: Asset,
        asset2: Asset,
        window_days: int,
    ) -> Optional[float]:
        """Calculate correlation between two assets"""
        # Would fetch historical prices and calculate correlation
        # For now, return None
        return None


class ExchangeOutageWatchdog(BaseWatchdog):
    """
    Monitors exchange health endpoints

    Detects:
    - Exchange outages
    - API degradation
    - Slow response times
    """

    def __init__(self, check_interval: int = 60, **kwargs: Any):  # 1 minute
        super().__init__(check_interval=check_interval, **kwargs)
        self._exchanges = {
            "binance": "https://api.binance.com/api/v3/ping",
            "coinbase": "https://api.coinbase.com/v2/time",
            "kraken": "https://api.kraken.com/0/public/Time",
        }
        self._timeout_threshold = 5.0  # seconds

    @property
    def name(self) -> str:
        return "exchange_outage"

    async def check(self) -> Optional[WatchdogEvent]:
        """Check exchange health"""
        import aiohttp

        for exchange, health_url in self._exchanges.items():
            try:
                start_time = datetime.now(timezone.utc)

                async with aiohttp.ClientSession() as session, session.get(
                    health_url,
                    timeout=aiohttp.ClientTimeout(total=self._timeout_threshold)
                ) as response:
                    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()

                    if response.status != 200:
                        return WatchdogEvent(
                            type=EventType.EXCHANGE_OUTAGE,
                            severity=Severity.HIGH,
                            asset=None,
                            description=f"{exchange} is experiencing issues (HTTP {response.status})",
                            data={
                                "exchange": exchange,
                                "status_code": response.status,
                                "response_time_ms": elapsed * 1000,
                            },
                            watchdog=self.name,
                        )

                    # Check for slow response
                    if elapsed > self._timeout_threshold * 0.8:
                        return WatchdogEvent(
                            type=EventType.EXCHANGE_OUTAGE,
                            severity=Severity.MEDIUM,
                            asset=None,
                            description=f"{exchange} is responding slowly ({elapsed:.1f}s)",
                            data={
                                "exchange": exchange,
                                "response_time_ms": elapsed * 1000,
                            },
                            watchdog=self.name,
                        )

            except asyncio.TimeoutError:
                return WatchdogEvent(
                    type=EventType.EXCHANGE_OUTAGE,
                    severity=Severity.CRITICAL,
                    asset=None,
                    description=f"{exchange} is not responding (timeout)",
                    data={
                        "exchange": exchange,
                        "error": "timeout",
                    },
                    watchdog=self.name,
                )
            except Exception as e:
                logger.error(f"Error checking {exchange} health: {e}")

        return None


class PriceAnomalyWatchdog(BaseWatchdog):
    """
    Detects rapid price movements and flash crashes

    Detects:
    - Rapid price movements (>5% in 1 min)
    - Flash crashes
    - Cross-exchange arbitrage opportunities
    """

    def __init__(self, check_interval: int = 30, **kwargs: Any):  # 30 seconds
        super().__init__(check_interval=check_interval, **kwargs)
        self._monitored_symbols = ["BTC", "ETH", "SPY", "QQQ", "AAPL", "TSLA"]
        self._price_history: Dict[str, List[tuple[datetime, float]]] = {}
        self._rapid_move_threshold = 5.0  # 5% in 1 minute

    @property
    def name(self) -> str:
        return "price_anomaly"

    async def check(self) -> Optional[WatchdogEvent]:
        """Check for price anomalies"""
        from fiml.arbitration.engine import arbitration_engine

        for symbol in self._monitored_symbols:
            try:
                # Determine asset type
                asset_type = AssetType.CRYPTO if symbol in ["BTC", "ETH"] else AssetType.EQUITY
                asset = Asset(symbol=symbol, asset_type=asset_type)

                # Get current price via arbitration engine
                plan = await arbitration_engine.arbitrate_request(
                    asset=asset,
                    data_type=DataType.PRICE,
                )
                response = await arbitration_engine.execute_with_fallback(
                    plan=plan,
                    asset=asset,
                    data_type=DataType.PRICE,
                )

                if not response or not response.data or "price" not in response.data:
                    continue

                current_data = response.data

                current_price = current_data["price"]
                current_time = datetime.now(timezone.utc)

                # Initialize price history
                if symbol not in self._price_history:
                    self._price_history[symbol] = []

                # Add to history
                self._price_history[symbol].append((current_time, current_price))

                # Keep only last 2 minutes
                cutoff_time = current_time - timedelta(minutes=2)
                self._price_history[symbol] = [
                    (t, p) for t, p in self._price_history[symbol]
                    if t > cutoff_time
                ]

                # Check for rapid movement (need at least 2 data points)
                if len(self._price_history[symbol]) < 2:
                    continue

                # Get price from 1 minute ago
                minute_ago = current_time - timedelta(minutes=1)
                past_prices = [
                    p for t, p in self._price_history[symbol]
                    if t <= minute_ago
                ]

                if not past_prices:
                    continue

                past_price = past_prices[-1]
                price_change_pct = ((current_price - past_price) / past_price) * 100

                # Detect rapid movement
                if abs(price_change_pct) > self._rapid_move_threshold:
                    severity = Severity.CRITICAL if abs(price_change_pct) > 10 else Severity.HIGH

                    event_type = EventType.FLASH_CRASH if price_change_pct < -10 else EventType.PRICE_ANOMALY

                    return WatchdogEvent(
                        type=event_type,
                        severity=severity,
                        asset=asset,
                        description=f"{symbol} rapid price movement: "
                                  f"{'+' if price_change_pct > 0 else ''}{price_change_pct:.2f}% in 1 min",
                        data={
                            "current_price": current_price,
                            "past_price": past_price,
                            "change_pct": price_change_pct,
                            "time_window_seconds": 60,
                        },
                        watchdog=self.name,
                    )
            except Exception as e:
                logger.error(f"Error checking price anomaly for {symbol}: {e}")

        return None


# Export all watchdogs
__all__ = [
    "EarningsAnomalyWatchdog",
    "UnusualVolumeWatchdog",
    "WhaleMovementWatchdog",
    "FundingRateWatchdog",
    "LiquidityDropWatchdog",
    "CorrelationBreakdownWatchdog",
    "ExchangeOutageWatchdog",
    "PriceAnomalyWatchdog",
]
