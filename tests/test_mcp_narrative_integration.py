"""
Integration tests for MCP narrative generation

Tests narrative generation flow with AAPL and BTC examples

NOTE: These tests require a real Azure OpenAI endpoint and are skipped
in standard test environments. They are meant for manual/integration testing.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from fiml.core.models import AnalysisDepth, Asset, AssetType, Market
from fiml.mcp.tools import get_narrative, search_by_coin, search_by_symbol

# Skip logic removed to enable tests with mocks
# pytestmark = pytest.mark.skipif(...)


@pytest.fixture(autouse=True)
def mock_azure_openai_httpx(monkeypatch):
    """
    Custom mock for narrative integration tests that handles different prompt types
    and forces mock endpoint usage.
    """
    # Force mock endpoint
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://mock-azure-openai.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "mock-key")

    from fiml.core.config import settings

    settings.azure_openai_endpoint = "https://mock-azure-openai.openai.azure.com/"
    settings.azure_openai_api_key = "mock-key"

    # Create mock response
    mock_response = MagicMock()
    mock_response.status_code = 200

    # Create a shared state for the mock response to access the request payload
    request_payload = {}

    def side_effect(*args, **kwargs):
        # Use the captured payload
        json_payload = request_payload.get("json", {})
        messages = json_payload.get("messages", [])
        user_content = next((m["content"] for m in messages if m["role"] == "user"), "")

        content = "Mock narrative content for testing. This is a longer sentence to ensure we meet the minimum length requirements for summaries and sections in the narrative generation tests. It needs to be at least 50 characters long."

        if "JSON array" in user_content or "extract insights" in user_content.lower():
            content = '["Insight 1: The market is showing strong bullish momentum based on recent price action.", "Insight 2: Technical indicators suggest overbought conditions in the short term.", "Insight 3: Fundamental metrics remain solid with healthy profit margins."]'
        elif "sentiment" in user_content.lower() and "JSON object" in messages[0].get(
            "content", ""
        ):
            content = '{"positive": 0.7, "negative": 0.1, "neutral": 0.2}'

        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": content,
                    },
                    "finish_reason": "stop",
                    "index": 0,
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
        }

    mock_response.json = MagicMock(side_effect=side_effect)

    # Patch httpx
    import httpx

    async def mock_post(self, url, *args, **kwargs):
        # Capture the payload
        request_payload["json"] = kwargs.get("json", {})
        return mock_response

    with patch.object(httpx.AsyncClient, "post", mock_post):
        yield


@pytest.fixture(autouse=True)
def mock_providers():
    """Mock provider responses for narrative integration tests"""
    from fiml.core.models import ArbitrationPlan, Asset, AssetType, DataType
    from fiml.providers.base import ProviderResponse

    mock_asset = Asset(symbol="AAPL", asset_type=AssetType.EQUITY)

    mock_response = ProviderResponse(
        provider="mock_provider",
        asset=mock_asset,
        data_type=DataType.PRICE,
        data={
            "price": 150.0,
            "change": 2.5,
            "change_percent": 1.69,
            "volume": 50000000,
            "market_cap": 2500000000000,
            "pe_ratio": 28.5,
            "dividend_yield": 0.5,
        },
        timestamp=datetime.now(timezone.utc),
        is_valid=True,
        is_fresh=True,
        confidence=1.0,
    )

    async def mock_arbitrate_request(*args, **kwargs):
        return ArbitrationPlan(
            primary_provider="mock_primary",
            fallback_providers=[],
            estimated_latency_ms=10,
        )

    async def mock_execute_with_fallback(*args, **kwargs):
        # Check which data type is being requested
        data_type = args[2] if len(args) > 2 else kwargs.get("data_type", DataType.PRICE)

        if data_type == DataType.FUNDAMENTALS:
            # Return fundamental data with PE ratio to trigger risk factor
            return ProviderResponse(
                provider="mock_provider",
                asset=mock_asset,
                data_type=DataType.FUNDAMENTALS,
                data={
                    "pe_ratio": 45.0,  # High PE ratio to trigger risk factor
                    "market_cap": 2500000000000,
                    "beta": 1.8,  # High beta to trigger risk factor
                },
                timestamp=datetime.now(timezone.utc),
                is_valid=True,
                is_fresh=True,
                confidence=1.0,
            )
        elif data_type == DataType.TECHNICAL:
            # Return technical data with high RSI to trigger risk factor
            return ProviderResponse(
                provider="mock_provider",
                asset=mock_asset,
                data_type=DataType.TECHNICAL,
                data={
                    "rsi": 75.0,  # Overbought RSI to trigger risk factor
                    "macd": {"macd": 2.5, "signal": 1.5, "histogram": 1.0},
                },
                timestamp=datetime.now(timezone.utc),
                is_valid=True,
                is_fresh=True,
                confidence=1.0,
            )
        else:
            # Return price data
            return mock_response

    with (
        patch(
            "fiml.arbitration.engine.arbitration_engine.arbitrate_request",
            side_effect=mock_arbitrate_request,
        ),
        patch(
            "fiml.arbitration.engine.arbitration_engine.execute_with_fallback",
            side_effect=mock_execute_with_fallback,
        ),
    ):
        yield


@pytest.fixture(autouse=True)
async def init_cache():
    """Initialize cache manager for tests"""
    from fiml.cache.manager import cache_manager

    # Initialize cache manager
    await cache_manager.initialize()

    # Flush Redis to prevent cache pollution between tests
    if cache_manager.l1._redis:
        await cache_manager.l1._redis.flushdb()

    yield

    # Flush again on teardown
    if cache_manager.l1._redis:
        await cache_manager.l1._redis.flushdb()

    await cache_manager.shutdown()


class TestMCPNarrativeIntegration:
    """Test MCP tools with narrative generation"""

    @pytest.mark.asyncio
    async def test_search_by_symbol_with_narrative_standard(self):
        """Test search_by_symbol with standard depth narrative"""
        response = await search_by_symbol(
            symbol="AAPL",
            market=Market.US,
            depth=AnalysisDepth.STANDARD,
            language="en",
            expertise_level="intermediate",
            include_narrative=True,
        )

        # Verify response structure
        assert response.symbol == "AAPL"
        assert response.cached is not None
        assert response.task is not None
        assert response.disclaimer is not None
        # Verify disclaimer includes LICENSE reference
        assert (
            "LICENSE" in response.disclaimer
        ), "API response disclaimer should reference LICENSE file"

        # Verify narrative is included
        assert response.narrative is not None
        assert response.narrative.summary is not None
        assert len(response.narrative.summary) > 50
        assert len(response.narrative.key_insights) > 0
        assert len(response.narrative.risk_factors) > 0
        assert response.narrative.language == "en"

    @pytest.mark.asyncio
    async def test_search_by_symbol_with_narrative_deep(self):
        """Test search_by_symbol with deep depth narrative (all sections)"""
        response = await search_by_symbol(
            symbol="AAPL",
            market=Market.US,
            depth=AnalysisDepth.DEEP,
            language="en",
            expertise_level="advanced",
            include_narrative=True,
        )

        # Verify narrative includes sentiment and risk (deep analysis)
        assert response.narrative is not None
        assert len(response.narrative.key_insights) > 0
        assert len(response.narrative.risk_factors) > 0
        # Deep analysis should have more comprehensive insights
        assert len(response.narrative.summary) > 100

    @pytest.mark.asyncio
    async def test_search_by_symbol_quick_no_narrative(self):
        """Test search_by_symbol with quick depth (no narrative)"""
        response = await search_by_symbol(
            symbol="AAPL",
            market=Market.US,
            depth=AnalysisDepth.QUICK,
            language="en",
            expertise_level="intermediate",
            include_narrative=True,  # Requested but won't generate for QUICK
        )

        # Quick depth should not generate narrative
        assert response.narrative is None

    @pytest.mark.asyncio
    async def test_search_by_symbol_narrative_disabled(self):
        """Test search_by_symbol with narrative disabled"""
        response = await search_by_symbol(
            symbol="AAPL",
            market=Market.US,
            depth=AnalysisDepth.STANDARD,
            language="en",
            expertise_level="intermediate",
            include_narrative=False,
        )

        # Should not generate narrative when disabled
        assert response.narrative is None

    @pytest.mark.asyncio
    async def test_search_by_symbol_multilingual(self):
        """Test search_by_symbol with different languages"""
        languages = ["en", "es", "fr"]

        for lang in languages:
            response = await search_by_symbol(
                symbol="AAPL",
                market=Market.US,
                depth=AnalysisDepth.STANDARD,
                language=lang,
                expertise_level="intermediate",
                include_narrative=True,
            )

            assert response.narrative is not None
            assert response.narrative.language == lang

    @pytest.mark.asyncio
    async def test_search_by_symbol_expertise_levels(self):
        """Test search_by_symbol with different expertise levels"""
        expertise_levels = ["beginner", "intermediate", "advanced", "quant"]

        for expertise in expertise_levels:
            response = await search_by_symbol(
                symbol="AAPL",
                market=Market.US,
                depth=AnalysisDepth.STANDARD,
                language="en",
                expertise_level=expertise,
                include_narrative=True,
            )

            assert response.narrative is not None
            # Narrative should be generated for all expertise levels

    @pytest.mark.asyncio
    async def test_search_by_coin_with_crypto_narrative(self):
        """Test search_by_coin with crypto-specific narrative"""
        response = await search_by_coin(
            symbol="BTC",
            exchange="Binance",
            pair="USD",
            depth=AnalysisDepth.STANDARD,
            language="en",
            expertise_level="intermediate",
            include_narrative=True,
        )

        # Verify crypto response
        assert response.symbol == "BTC"
        assert response.pair == "BTC/USD"
        assert response.crypto_metrics is not None

        # Verify crypto narrative is included
        assert response.narrative is not None
        assert response.narrative.summary is not None

        # Crypto should have specific risk warnings
        assert len(response.narrative.risk_factors) > 0
        # Check for crypto-specific risks
        risk_text = " ".join(response.narrative.risk_factors).lower()
        assert any(
            keyword in risk_text for keyword in ["volatility", "24/7", "regulatory", "crypto"]
        )

    @pytest.mark.asyncio
    async def test_search_by_coin_deep_analysis(self):
        """Test search_by_coin with deep analysis (blockchain metrics)"""
        response = await search_by_coin(
            symbol="BTC",
            exchange="Coinbase",
            pair="USD",
            depth=AnalysisDepth.DEEP,
            language="en",
            expertise_level="advanced",
            include_narrative=True,
        )

        # Deep crypto analysis should include comprehensive insights
        assert response.narrative is not None
        assert len(response.narrative.key_insights) >= 2
        # Should mention exchange and trading pair
        insights_text = " ".join(response.narrative.key_insights)
        assert "Coinbase" in insights_text or "exchange" in insights_text.lower()

    @pytest.mark.asyncio
    async def test_get_narrative_standalone(self):
        """Test standalone narrative generation"""
        analysis_data = {
            "name": "Apple Inc.",
            "region": "US",
            "sources": ["yahoo_finance"],
            "price_data": {
                "price": 175.50,
                "change": 2.30,
                "change_percent": 1.33,
                "volume": 50000000,
            },
            "technical_data": {
                "trend": "bullish",
                "strength": "strong",
                "rsi": 65,
            },
            "fundamental_data": {
                "market_cap": 2800000000000,
                "pe_ratio": 28.5,
                "sector": "Technology",
            },
        }

        result = await get_narrative(
            symbol="AAPL",
            asset_type="equity",
            language="en",
            expertise_level="intermediate",
            analysis_data=analysis_data,
        )

        # Verify result structure
        assert result["symbol"] == "AAPL"
        assert result["asset_type"] == "equity"
        assert result["language"] == "en"
        assert "narrative" in result

        # Verify narrative content
        narrative = result["narrative"]
        assert narrative["summary"] is not None
        assert len(narrative["key_insights"]) > 0
        assert len(narrative["sections"]) > 0
        assert "full_text" in narrative
        assert "markdown" in narrative
        assert narrative["word_count"] > 0

    @pytest.mark.asyncio
    async def test_get_narrative_focus_areas(self):
        """Test narrative generation with specific focus areas"""
        analysis_data = {
            "name": "Bitcoin",
            "region": "GLOBAL",
            "sources": ["binance"],
            "price_data": {
                "price": 42000.0,
                "change": -500.0,
                "change_percent": -1.18,
            },
            "risk_data": {
                "volatility_risk": "high",
                "regulatory_risk": "high",
            },
        }

        result = await get_narrative(
            symbol="BTC/USD",
            asset_type="crypto",
            language="en",
            expertise_level="beginner",
            analysis_data=analysis_data,
            focus_areas=["market", "risk"],  # Only market and risk
        )

        assert "narrative" in result
        narrative = result["narrative"]

        # Should focus on market and risk
        assert len(narrative["sections"]) > 0
        section_types = [s["type"] for s in narrative["sections"]]
        # Should include market context and risk
        assert any("market" in t or "risk" in t for t in section_types)

    @pytest.mark.asyncio
    async def test_narrative_caching(self):
        """Test that narratives are cached and reused"""
        # First call generates narrative
        await get_narrative(
            symbol="AAPL",
            asset_type="equity",
            language="en",
            expertise_level="intermediate",
            analysis_data={"price_data": {"price": 175.0, "change": 1.0, "change_percent": 0.57}},
        )

        # Second call with same params should use cache
        result2 = await get_narrative(
            symbol="AAPL",
            asset_type="equity",
            language="en",
            expertise_level="intermediate",
            analysis_data={"price_data": {"price": 175.0, "change": 1.0, "change_percent": 0.57}},
        )

        # Second result should be cached
        assert result2.get("cached") is True

    @pytest.mark.asyncio
    async def test_narrative_error_handling(self):
        """Test narrative generation with invalid data (graceful fallback)"""
        # Should handle missing data gracefully
        result = await get_narrative(
            symbol="INVALID",
            asset_type="equity",
            language="en",
            expertise_level="intermediate",
            analysis_data=None,  # No data provided
        )

        # Should still return a result (may be basic or error)
        assert "symbol" in result
        # Either has narrative or error
        assert "narrative" in result or "error" in result

    @pytest.mark.asyncio
    async def test_narrative_formatting_text(self):
        """Test narrative text formatting"""
        from fiml.mcp.tools import format_narrative_text
        from fiml.narrative.models import (Narrative, NarrativeSection,
                                           NarrativeType)

        # Create test narrative
        narrative = Narrative(
            summary="This is a comprehensive test summary with sufficient length to meet validation requirements.",
            sections=[
                NarrativeSection(
                    title="Market Context",
                    content="Market is bullish.",
                    section_type=NarrativeType.MARKET_CONTEXT,
                )
            ],
            key_insights=["Insight 1", "Insight 2"],
            risk_factors=["Risk 1"],
            disclaimer="Test disclaimer",
        )

        text = format_narrative_text(narrative)

        # Verify formatting
        assert "EXECUTIVE SUMMARY" in text
        assert "This is a comprehensive test summary" in text
        assert "MARKET CONTEXT" in text
        assert "Market is bullish" in text
        assert "KEY INSIGHTS" in text
        assert "RISK FACTORS" in text
        assert "DISCLAIMER" in text

    @pytest.mark.asyncio
    async def test_narrative_formatting_markdown(self):
        """Test narrative markdown formatting"""
        from fiml.mcp.tools import format_narrative_markdown
        from fiml.narrative.models import (Narrative, NarrativeSection,
                                           NarrativeType)

        # Create test narrative
        narrative = Narrative(
            summary="This is a comprehensive test summary with sufficient length to meet validation requirements.",
            sections=[
                NarrativeSection(
                    title="Market Context",
                    content="Market is bullish.",
                    section_type=NarrativeType.MARKET_CONTEXT,
                )
            ],
            key_insights=["Insight 1"],
            risk_factors=["Risk 1"],
            disclaimer="Test disclaimer",
        )

        markdown = format_narrative_markdown(narrative)

        # Verify markdown formatting
        assert "# Executive Summary" in markdown
        assert "## Market Context" in markdown
        assert "## Key Insights" in markdown
        assert "## Risk Factors" in markdown
        assert "- Insight 1" in markdown
        assert "- Risk 1" in markdown
        assert "*Test disclaimer*" in markdown


class TestNarrativeTTLCalculation:
    """Test dynamic TTL calculation for narratives"""

    def test_crypto_high_volatility_ttl(self):
        """Test crypto TTL with high volatility"""
        from fiml.mcp.tools import calculate_narrative_ttl

        asset = Asset(symbol="BTC/USD", asset_type=AssetType.CRYPTO)
        ttl = calculate_narrative_ttl(asset, volatility=12.5)

        # High volatility (>10%) should have 3 minute TTL
        assert ttl == 180

    def test_crypto_moderate_volatility_ttl(self):
        """Test crypto TTL with moderate volatility"""
        from fiml.mcp.tools import calculate_narrative_ttl

        asset = Asset(symbol="BTC/USD", asset_type=AssetType.CRYPTO)
        ttl = calculate_narrative_ttl(asset, volatility=7.0)

        # Medium volatility (5-10%) should have 5 minute TTL
        assert ttl == 300

    def test_crypto_low_volatility_ttl(self):
        """Test crypto TTL with low volatility"""
        from fiml.mcp.tools import calculate_narrative_ttl

        asset = Asset(symbol="BTC/USD", asset_type=AssetType.CRYPTO)
        ttl = calculate_narrative_ttl(asset, volatility=2.0)

        # Low volatility should have 10 minute TTL
        assert ttl == 600

    def test_equity_high_volatility_ttl(self):
        """Test equity TTL with high volatility during market hours"""
        from fiml.mcp.tools import calculate_narrative_ttl

        asset = Asset(symbol="AAPL", asset_type=AssetType.EQUITY)
        ttl = calculate_narrative_ttl(asset, volatility=4.0)

        # High volatility (>3%) during market hours: 5 minutes
        # Note: This test may vary based on current time
        assert ttl in [300, 600, 900, 1800]  # Possible values based on time

    def test_equity_moderate_volatility_ttl(self):
        """Test equity TTL with moderate volatility"""
        from fiml.mcp.tools import calculate_narrative_ttl

        asset = Asset(symbol="AAPL", asset_type=AssetType.EQUITY)
        ttl = calculate_narrative_ttl(asset, volatility=1.5)

        # Moderate volatility (1-3%): 10 minutes or more
        assert ttl in [600, 900, 1800]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
