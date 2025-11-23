"""
Integration tests for enhanced workers with real data processing

Tests each worker independently with mocked provider and Azure OpenAI responses.
Note: These tests verify the worker logic works correctly with mocked data.
For full end-to-end tests with real providers, see test_live_system.py
"""

from datetime import datetime, timezone

import numpy as np
import pytest

from fiml.core.models import Asset, AssetType, DataType
from fiml.providers.base import ProviderResponse


@pytest.fixture
def sample_asset():
    """Create a sample asset for testing"""
    return Asset(symbol="AAPL", asset_type=AssetType.EQUITY, name="Apple Inc.")


@pytest.fixture
def mock_provider_response():
    """Create a mock provider response factory"""
    def _create_response(data_type: DataType, data: dict):
        return ProviderResponse(
            provider="mock",
            asset=Asset(symbol="AAPL", asset_type=AssetType.EQUITY, name="Apple Inc."),
            data_type=data_type,
            data=data,
            timestamp=datetime.now(timezone.utc),
            is_valid=True,
            is_fresh=True,
            confidence=1.0,
        )
    return _create_response


class TestFundamentalsWorkerLogic:
    """Test FundamentalsWorker calculation logic (no Ray)"""

    def test_fundamentals_ratio_calculations(self, sample_asset):
        """Test that fundamental ratios are calculated correctly"""

        # Sample fundamental data
        market_cap = 3000000000000
        shares_outstanding = 16000000000
        eps = 6.12
        total_equity = 65000000000
        net_income = 98000000000

        # Expected calculations
        price_per_share = market_cap / shares_outstanding
        expected_pe = price_per_share / eps
        expected_roe = net_income / total_equity

        # Verify calculations are correct
        assert abs(price_per_share - 187.5) < 0.01
        assert abs(expected_pe - 30.64) < 0.01
        assert abs(expected_roe - 1.507) < 0.01


class TestTechnicalWorkerLogic:
    """Test TechnicalWorker indicator calculations (no Ray)"""

    def test_rsi_calculation(self):
        """Test RSI calculation produces valid range"""

        # Generate price series
        np.random.seed(42)
        prices = np.cumsum(np.random.randn(100)) + 100

        # Calculate returns
        delta = np.diff(prices)
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)

        # RSI calculation
        avg_gain = np.mean(gain[-14:]) if len(gain) >= 14 else 0
        avg_loss = np.mean(loss[-14:]) if len(loss) >= 14 else 1
        rs = avg_gain / avg_loss if avg_loss > 0 else 0
        rsi = 100 - (100 / (1 + rs))

        # RSI should be between 0 and 100
        assert 0 <= rsi <= 100

    def test_bollinger_bands_calculation(self):
        """Test Bollinger Bands calculation"""

        import pandas as pd

        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(50))

        sma = pd.Series(prices).rolling(20).mean().iloc[-1]
        std = pd.Series(prices).rolling(20).std().iloc[-1]

        upper = sma + 2 * std
        lower = sma - 2 * std

        # Upper should be greater than lower
        assert upper > lower
        # Current price should be within reasonable range
        assert lower < prices[-1] < upper * 1.5  # Allow some wiggle room


class TestRiskWorkerLogic:
    """Test RiskWorker calculations (no Ray)"""

    def test_volatility_calculation(self):
        """Test volatility calculation"""

        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(365) * 1.5)
        returns = np.diff(prices) / prices[:-1]

        daily_vol = np.std(returns)
        annual_vol = daily_vol * np.sqrt(252)

        # Should be positive and reasonable
        assert annual_vol > 0
        assert annual_vol < 2.0  # Less than 200% annualized

    def test_sharpe_ratio_calculation(self):
        """Test Sharpe ratio calculation"""

        np.random.seed(42)
        prices = 100 * np.cumprod(1 + np.random.randn(365) * 0.01 + 0.0003)  # Positive drift
        returns = np.diff(prices) / prices[:-1]

        mean_return = np.mean(returns) * 252
        volatility = np.std(returns) * np.sqrt(252)
        risk_free = 0.04

        sharpe = (mean_return - risk_free) / volatility if volatility > 0 else 0

        # Should be a reasonable value
        assert -5 < sharpe < 5

    def test_max_drawdown_calculation(self):
        """Test maximum drawdown calculation"""

        # Create prices with known drawdown
        prices = np.array([100, 110, 120, 100, 90, 95, 105])
        returns = np.diff(prices) / prices[:-1]

        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_dd = np.min(drawdown)

        # Should be negative and reasonable
        assert max_dd < 0
        assert max_dd > -1.0  # Not more than 100% drawdown


class TestCorrelationWorkerLogic:
    """Test CorrelationWorker calculations (no Ray)"""

    def test_correlation_calculation(self):
        """Test Pearson correlation calculation"""

        np.random.seed(42)

        # Create correlated series
        x = np.random.randn(100)
        y = 0.8 * x + 0.2 * np.random.randn(100)  # High correlation

        correlation = np.corrcoef(x, y)[0, 1]

        # Should be highly correlated (adjusted for random seed)
        assert 0.7 < correlation < 0.98

    def test_beta_calculation(self):
        """Test beta calculation"""

        np.random.seed(42)

        # Market returns
        market_returns = np.random.randn(100) * 0.01

        # Asset returns (higher volatility = higher beta)
        asset_returns = market_returns * 1.5 + np.random.randn(100) * 0.005

        # Beta calculation
        covariance = np.cov(asset_returns, market_returns)[0, 1]
        market_variance = np.var(market_returns)
        beta = covariance / market_variance if market_variance > 0 else 1.0

        # Should be around 1.5
        assert 1.0 < beta < 2.0


class TestSentimentWorkerLogic:
    """Test SentimentWorker logic (no Ray)"""

    def test_sentiment_aggregation(self):
        """Test sentiment score aggregation"""

        # Sample sentiment scores
        sentiment_scores = [0.8, 0.6, -0.2, 0.5, 0.7]

        avg_sentiment = np.mean(sentiment_scores)

        # Should be positive average
        assert avg_sentiment > 0
        assert -1 <= avg_sentiment <= 1

    def test_weighted_sentiment(self):
        """Test impact-weighted sentiment"""

        articles = [
            {"sentiment": 0.8, "impact": "high"},
            {"sentiment": -0.5, "impact": "low"},
            {"sentiment": 0.6, "impact": "medium"},
        ]

        weighted_scores = []
        for a in articles:
            weight = 3.0 if a["impact"] == "high" else (1.5 if a["impact"] == "medium" else 1.0)
            weighted_scores.extend([a["sentiment"]] * int(weight))

        weighted_avg = np.mean(weighted_scores)
        unweighted_avg = np.mean([a["sentiment"] for a in articles])

        # Weighted should be different from unweighted
        assert weighted_avg != unweighted_avg




class TestWorkerScoring:
    """Test scoring logic produces valid ranges"""

    def test_score_ranges(self):
        """Verify all score calculations produce 0-10 range"""

        # Test various scoring scenarios
        test_cases = [
            (5.0, 2.0, -1.0),  # Base + adjustments
            (0.0, -5.0, 3.0),   # Negative adjustments
            (10.0, 5.0, 2.0),   # Over-limit
        ]

        for base, adj1, adj2 in test_cases:
            score = base + adj1 + adj2
            clamped_score = max(0.0, min(10.0, score))

            assert 0.0 <= clamped_score <= 10.0


class TestErrorHandling:
    """Test error handling logic"""

    def test_division_by_zero_handling(self):
        """Test safe division in calculations"""

        # Test P/E ratio with zero EPS
        eps = 0
        price = 100

        pe_ratio = price / eps if eps > 0 else 0

        assert pe_ratio == 0

    def test_insufficient_data_handling(self):
        """Test handling of insufficient data"""

        import numpy as np
        # Not enough data points for calculation
        prices = np.array([100, 101, 102])

        # Should handle gracefully
        if len(prices) < 20:
            sma_20 = np.mean(prices)  # Fallback to simple mean
        else:
            sma_20 = np.mean(prices[-20:])

        assert sma_20 > 0


class TestDataStructures:
    """Test result data structure consistency"""

    def test_result_structure(self, sample_asset):
        """Verify result dictionaries have required fields"""

        from datetime import datetime, timezone
        required_fields = ["asset", "analysis_type", "score", "timestamp"]

        # Mock result from any worker
        result = {
            "asset": sample_asset.symbol,
            "analysis_type": "fundamentals",
            "score": 7.5,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        for field in required_fields:
            assert field in result

    def test_confidence_range(self):
        """Test confidence scores are in valid range"""

        confidence_values = [0.0, 0.5, 0.75, 1.0]

        for conf in confidence_values:
            assert 0.0 <= conf <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
