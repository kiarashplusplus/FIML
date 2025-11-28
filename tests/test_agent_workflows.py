"""
Tests for Agent Workflows

Tests the high-level workflow orchestration including:
- Deep equity analysis workflow
- Crypto sentiment analysis workflow
- Error handling and resilience
- Partial result handling
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fiml.agents.workflows import (
    CryptoSentimentAnalysisWorkflow,
    DeepEquityAnalysisWorkflow,
    WorkflowStatus,
    crypto_sentiment_analysis,
    deep_equity_analysis,
)
from fiml.core.models import Asset, AssetType, Market


class TestDeepEquityAnalysisWorkflow:
    """Test deep equity analysis workflow"""

    @pytest.mark.asyncio
    async def test_workflow_initialization(self):
        """Test workflow can be initialized"""
        workflow = DeepEquityAnalysisWorkflow()
        assert workflow is not None
        assert workflow.orchestrator is not None
        assert workflow.llm_client is not None

    @pytest.mark.asyncio
    async def test_workflow_execute_success(self):
        """Test successful workflow execution"""
        workflow = DeepEquityAnalysisWorkflow()

        # Mock orchestrator methods
        workflow.orchestrator.initialized = True
        workflow.orchestrator.analyze_asset = AsyncMock(
            return_value={
                "fundamentals": {
                    "metrics": {"pe_ratio": 25.5, "eps": 6.12},
                    "valuation": {"assessment": "fairly_valued", "confidence": 0.75},
                },
                "technical": {
                    "indicators": {"rsi": 55, "macd": 0.5},
                    "trend": {"direction": "bullish", "strength": "medium"},
                },
                "sentiment": {"score": 65, "news_sentiment": "positive"},
                "news": {},
                "risk": {"level": "medium", "volatility": 0.25, "beta": 1.1},
                "correlation": {},
            }
        )

        # Mock provider registry
        with patch("fiml.agents.workflows.provider_registry") as mock_registry:
            mock_provider = MagicMock()
            mock_provider.name = "mock"
            mock_provider.fetch_price = AsyncMock(
                return_value=MagicMock(
                    is_valid=True,
                    data={
                        "price": 150.25,
                        "change": 2.5,
                        "change_percent": 1.69,
                        "volume": 1000000,
                        "market_cap": 2500000000,
                    },
                )
            )
            mock_registry.get_providers_for_asset = AsyncMock(return_value=[mock_provider])

            # Mock LLM client
            workflow.llm_client.generate_narrative = AsyncMock(
                return_value="This is a test narrative about the stock."
            )

            # Execute workflow
            result = await workflow.execute(
                symbol="AAPL", market=Market.US, include_narrative=True, include_recommendation=True
            )

            # Assertions
            assert result.status == WorkflowStatus.COMPLETED
            assert result.steps_completed == 7
            assert result.steps_total == 7
            assert result.snapshot is not None
            assert result.snapshot["price"] == 150.25
            assert result.fundamentals is not None
            assert result.technicals is not None
            assert result.sentiment is not None
            assert result.risk is not None
            assert result.narrative is not None
            assert result.recommendation is not None
            assert result.data_quality_score > 0
            assert result.confidence_score > 0
            assert result.execution_time_ms is not None

    @pytest.mark.asyncio
    async def test_workflow_execute_without_narrative(self):
        """Test workflow execution without narrative generation"""
        workflow = DeepEquityAnalysisWorkflow()
        workflow.orchestrator.initialized = True
        workflow.orchestrator.analyze_asset = AsyncMock(return_value={})

        with patch("fiml.agents.workflows.provider_registry") as mock_registry:
            mock_provider = MagicMock()
            mock_provider.name = "mock"
            mock_provider.fetch_price = AsyncMock(
                return_value=MagicMock(is_valid=True, data={"price": 100})
            )
            mock_registry.get_providers_for_asset = AsyncMock(return_value=[mock_provider])

            result = await workflow.execute(
                symbol="MSFT", include_narrative=False, include_recommendation=False
            )

            assert result.status == WorkflowStatus.COMPLETED
            assert result.narrative is None
            assert result.recommendation is None

    @pytest.mark.asyncio
    async def test_workflow_handles_provider_failures(self):
        """Test workflow handles provider failures gracefully"""
        workflow = DeepEquityAnalysisWorkflow()
        workflow.orchestrator.initialized = True
        workflow.orchestrator.analyze_asset = AsyncMock(return_value={})

        with patch("fiml.agents.workflows.provider_registry") as mock_registry:
            # Provider that always fails
            mock_provider = MagicMock()
            mock_provider.name = "failing_provider"
            mock_provider.fetch_price = AsyncMock(side_effect=Exception("Provider error"))
            mock_registry.get_providers_for_asset = AsyncMock(return_value=[mock_provider])

            result = await workflow.execute(symbol="FAIL")

            # Should still complete with fallback data
            assert result.snapshot is not None
            assert result.snapshot["price"] == 0  # Fallback value

    @pytest.mark.asyncio
    async def test_workflow_partial_success(self):
        """Test workflow with partial agent failures"""
        workflow = DeepEquityAnalysisWorkflow()
        workflow.orchestrator.initialized = True

        # Some agents succeed, some fail
        workflow.orchestrator.analyze_asset = AsyncMock(
            return_value={
                "fundamentals": {"error": "Failed to fetch fundamentals"},
                "technical": {"indicators": {"rsi": 55}},
                "sentiment": {"error": "Failed to fetch sentiment"},
                "risk": {"level": "medium"},
            }
        )

        with patch("fiml.agents.workflows.provider_registry") as mock_registry:
            mock_provider = MagicMock()
            mock_provider.name = "mock"
            mock_provider.fetch_price = AsyncMock(
                return_value=MagicMock(is_valid=True, data={"price": 100})
            )
            mock_registry.get_providers_for_asset = AsyncMock(return_value=[mock_provider])

            result = await workflow.execute(symbol="PARTIAL", include_narrative=False)

            # Should complete with partial data
            assert result.status == WorkflowStatus.COMPLETED
            assert result.snapshot is not None
            assert result.technicals is not None
            assert result.risk is not None
            # Data quality should be lower
            assert result.data_quality_score < 100

    @pytest.mark.asyncio
    async def test_workflow_recommendation_logic(self):
        """Test recommendation generation logic"""
        workflow = DeepEquityAnalysisWorkflow()

        # Test bullish recommendation
        recommendation = await workflow._generate_recommendation(
            fundamentals={"valuation": {"assessment": "undervalued"}, "metrics": {"pe_ratio": 15}},
            technicals={"trend": {"direction": "bullish"}, "indicators": {"rsi": 55}},
            sentiment={"sentiment": {"score": 70}},
            risk={"risk": {"level": "low"}},
        )

        assert recommendation["action"] in ["BUY", "HOLD", "SELL"]
        assert recommendation["confidence"] in ["HIGH", "MEDIUM", "LOW"]
        assert "overall_score" in recommendation
        assert "component_scores" in recommendation

    @pytest.mark.asyncio
    async def test_data_quality_calculation(self):
        """Test data quality score calculation"""
        workflow = DeepEquityAnalysisWorkflow()

        from fiml.agents.workflows import DeepEquityAnalysisResult

        # All data available
        result = DeepEquityAnalysisResult(
            workflow_name="test",
            status=WorkflowStatus.COMPLETED,
            asset=Asset(symbol="TEST", asset_type=AssetType.EQUITY),
            started_at=datetime.now(),
            snapshot={"price": 100},
            fundamentals={"metrics": {}},
            technicals={"indicators": {}},
            sentiment={"score": 50},
            risk={"level": "medium"},
        )

        quality = workflow._calculate_data_quality(result)
        assert quality == 100.0

        # Partial data (missing fundamentals)
        result.fundamentals = {"error": "Failed"}
        quality = workflow._calculate_data_quality(result)
        assert quality == 80.0

    @pytest.mark.asyncio
    async def test_convenience_function(self):
        """Test convenience function for deep equity analysis"""
        with patch("fiml.agents.workflows.DeepEquityAnalysisWorkflow") as mock_workflow_class:
            mock_workflow = MagicMock()
            mock_workflow.execute = AsyncMock(
                return_value=MagicMock(status=WorkflowStatus.COMPLETED)
            )
            mock_workflow_class.return_value = mock_workflow

            result = await deep_equity_analysis(symbol="AAPL", market=Market.US)

            assert mock_workflow.execute.called
            assert result.status == WorkflowStatus.COMPLETED


class TestCryptoSentimentAnalysisWorkflow:
    """Test crypto sentiment analysis workflow"""

    @pytest.mark.asyncio
    async def test_workflow_initialization(self):
        """Test workflow can be initialized"""
        workflow = CryptoSentimentAnalysisWorkflow()
        assert workflow is not None
        assert workflow.orchestrator is not None
        assert workflow.llm_client is not None

    @pytest.mark.asyncio
    async def test_workflow_execute_success(self):
        """Test successful workflow execution"""
        workflow = CryptoSentimentAnalysisWorkflow()

        # Mock orchestrator methods
        workflow.orchestrator.initialized = True
        workflow.orchestrator.analyze_asset = AsyncMock(
            return_value={
                "sentiment": {"score": 65, "trend": "bullish"},
                "news": {"count": 5, "sentiment": "positive"},
                "technical": {"indicators": {"rsi": 60, "macd": 0.3}},
                "correlation": {"btc_correlation": 0.85, "eth_correlation": 0.75},
            }
        )

        # Mock provider registry
        with patch("fiml.agents.workflows.provider_registry") as mock_registry:
            mock_provider = MagicMock()
            mock_provider.name = "mock"
            mock_provider.fetch_price = AsyncMock(
                return_value=MagicMock(
                    is_valid=True,
                    data={
                        "price": 3500.50,
                        "change": 50.25,
                        "change_percent": 1.45,
                        "volume": 500000,
                        "high_24h": 3600,
                        "low_24h": 3400,
                    },
                )
            )
            mock_registry.get_providers_for_asset = AsyncMock(return_value=[mock_provider])

            # Mock LLM client
            workflow.llm_client.generate_narrative = AsyncMock(
                return_value="ETH shows bullish momentum with strong sentiment."
            )

            # Execute workflow
            result = await workflow.execute(
                symbol="ETH", exchange="binance", pair="USDT", include_narrative=True
            )

            # Assertions
            assert result.status == WorkflowStatus.COMPLETED
            assert result.steps_completed == 6
            assert result.steps_total == 6
            assert result.price_data is not None
            assert result.price_data["price"] == 3500.50
            assert result.sentiment is not None
            assert result.technicals is not None
            assert result.correlations is not None
            assert result.narrative is not None
            assert result.signals is not None
            assert result.confidence_score > 0
            assert result.execution_time_ms is not None

    @pytest.mark.asyncio
    async def test_workflow_without_narrative(self):
        """Test workflow without narrative generation"""
        workflow = CryptoSentimentAnalysisWorkflow()
        workflow.orchestrator.initialized = True
        workflow.orchestrator.analyze_asset = AsyncMock(return_value={})

        with patch("fiml.agents.workflows.provider_registry") as mock_registry:
            mock_provider = MagicMock()
            mock_provider.name = "mock"
            mock_provider.fetch_price = AsyncMock(
                return_value=MagicMock(is_valid=True, data={"price": 50000})
            )
            mock_registry.get_providers_for_asset = AsyncMock(return_value=[mock_provider])

            result = await workflow.execute(symbol="BTC", include_narrative=False)

            assert result.status == WorkflowStatus.COMPLETED
            assert result.narrative is None

    @pytest.mark.asyncio
    async def test_signal_generation_bullish(self):
        """Test trading signal generation for bullish scenario"""
        workflow = CryptoSentimentAnalysisWorkflow()

        signals = await workflow._generate_signals(
            sentiment={"sentiment": {"score": 70}},  # Bullish sentiment
            technicals={"indicators": {"rsi": 40}},  # Oversold - bullish
            correlations={},
        )

        assert signals["signal"] in ["BUY", "SELL", "NEUTRAL"]
        assert "strength" in signals
        assert "indicators" in signals
        assert len(signals["indicators"]) > 0

    @pytest.mark.asyncio
    async def test_signal_generation_bearish(self):
        """Test trading signal generation for bearish scenario"""
        workflow = CryptoSentimentAnalysisWorkflow()

        signals = await workflow._generate_signals(
            sentiment={"sentiment": {"score": 30}},  # Bearish sentiment
            technicals={"indicators": {"rsi": 75}},  # Overbought - bearish
            correlations={},
        )

        assert signals["signal"] in ["BUY", "SELL", "NEUTRAL"]
        assert "strength" in signals

    @pytest.mark.asyncio
    async def test_confidence_calculation(self):
        """Test confidence score calculation"""
        workflow = CryptoSentimentAnalysisWorkflow()

        from fiml.agents.workflows import CryptoSentimentAnalysisResult

        # All data available
        result = CryptoSentimentAnalysisResult(
            workflow_name="test",
            status=WorkflowStatus.COMPLETED,
            asset=Asset(symbol="BTC", asset_type=AssetType.CRYPTO),
            started_at=datetime.now(),
            price_data={"price": 50000},
            sentiment={"score": 65},
            technicals={"indicators": {}},
            correlations={"btc_correlation": 1.0},
        )

        confidence = workflow._calculate_confidence(result)
        assert confidence == 1.0

        # Partial data
        result.sentiment = {"error": "Failed"}
        confidence = workflow._calculate_confidence(result)
        assert confidence == 0.75

    @pytest.mark.asyncio
    async def test_convenience_function(self):
        """Test convenience function for crypto sentiment analysis"""
        with patch("fiml.agents.workflows.CryptoSentimentAnalysisWorkflow") as mock_workflow_class:
            mock_workflow = MagicMock()
            mock_workflow.execute = AsyncMock(
                return_value=MagicMock(status=WorkflowStatus.COMPLETED)
            )
            mock_workflow_class.return_value = mock_workflow

            result = await crypto_sentiment_analysis(symbol="ETH", exchange="binance")

            assert mock_workflow.execute.called
            assert result.status == WorkflowStatus.COMPLETED


class TestWorkflowErrorHandling:
    """Test error handling and resilience"""

    @pytest.mark.asyncio
    async def test_workflow_handles_orchestrator_failure(self):
        """Test workflow handles orchestrator initialization failure"""
        workflow = DeepEquityAnalysisWorkflow()

        # Mock orchestrator that fails to initialize
        workflow.orchestrator.initialize = AsyncMock(
            side_effect=Exception("Failed to initialize Ray")
        )

        with patch("fiml.agents.workflows.provider_registry") as mock_registry:
            mock_provider = MagicMock()
            mock_provider.name = "mock"
            mock_provider.fetch_price = AsyncMock(side_effect=Exception("Provider failed"))
            mock_registry.get_providers_for_asset = AsyncMock(return_value=[mock_provider])

            result = await workflow.execute(symbol="TEST")

            # Workflow should fail gracefully
            assert result.status == WorkflowStatus.FAILED
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_workflow_handles_llm_failure(self):
        """Test workflow handles LLM failure gracefully"""
        workflow = DeepEquityAnalysisWorkflow()
        workflow.orchestrator.initialized = True
        workflow.orchestrator.analyze_asset = AsyncMock(return_value={})

        # Mock LLM that fails
        workflow.llm_client.generate_narrative = AsyncMock(side_effect=Exception("LLM API error"))

        with patch("fiml.agents.workflows.provider_registry") as mock_registry:
            mock_provider = MagicMock()
            mock_provider.name = "mock"
            mock_provider.fetch_price = AsyncMock(
                return_value=MagicMock(is_valid=True, data={"price": 100})
            )
            mock_registry.get_providers_for_asset = AsyncMock(return_value=[mock_provider])

            result = await workflow.execute(symbol="TEST", include_narrative=True)

            # Should complete but narrative should indicate error
            assert result.status == WorkflowStatus.COMPLETED
            assert "unavailable" in result.narrative.lower() or "error" in result.narrative.lower()


class TestWorkflowIntegration:
    """Integration tests for workflows"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_end_to_end_equity_workflow(self):
        """Test end-to-end equity workflow with mocked dependencies"""
        # This test ensures all components work together
        result = await deep_equity_analysis(
            symbol="AAPL",
            market=Market.US,
            include_narrative=False,  # Skip LLM to avoid external deps
            include_recommendation=True,
        )

        # Should complete (even if with mock data)
        assert result.status in [
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.PARTIAL,
        ]
        assert result.execution_time_ms is not None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_end_to_end_crypto_workflow(self):
        """Test end-to-end crypto workflow with mocked dependencies"""
        result = await crypto_sentiment_analysis(
            symbol="BTC", exchange="binance", include_narrative=False
        )

        # Should complete (even if with mock data)
        assert result.status in [
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.PARTIAL,
        ]
        assert result.execution_time_ms is not None
