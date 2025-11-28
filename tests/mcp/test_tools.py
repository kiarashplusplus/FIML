"""
Tests for MCP Tools
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fiml.compliance.router import ComplianceCheck
from fiml.core.models import (
    AnalysisDepth,
    Asset,
    AssetType,
    Market,
)
from fiml.mcp.tools import (
    calculate_narrative_ttl,
    format_narrative_markdown,
    format_narrative_text,
    search_by_coin,
    search_by_symbol,
    track_query_in_session,
    truncate_narrative,
)
from fiml.narrative.models import Narrative, NarrativeSection, NarrativeType


@pytest.fixture
def mock_asset():
    return Asset(symbol="AAPL", asset_type=AssetType.EQUITY, market=Market.US)


@pytest.fixture
def mock_narrative():
    return Narrative(
        summary="Test Summary " * 5,  # Make it long enough (>50 chars)
        sections=[
            NarrativeSection(
                title="Test Section",
                content="Test Content",
                section_type=NarrativeType.SUMMARY,
                confidence=0.9
            )
        ],
        key_insights=["Insight 1"],
        risk_factors=["Risk 1"],
        disclaimer="Test Disclaimer"
    )


@pytest.mark.asyncio
async def test_search_by_symbol_success():
    """Test search_by_symbol with successful data fetch"""

    # Mock dependencies
    with patch("fiml.compliance.router.compliance_router.check_compliance", new_callable=AsyncMock) as mock_compliance, \
         patch("fiml.arbitration.engine.arbitration_engine.arbitrate_request", new_callable=AsyncMock), \
         patch("fiml.arbitration.engine.arbitration_engine.execute_with_fallback", new_callable=AsyncMock), \
         patch("fiml.cache.manager.cache_manager.get_with_read_through", new_callable=AsyncMock) as mock_cache, \
         patch("fiml.monitoring.task_registry.task_registry.register"):

        # Setup mocks
        mock_compliance.return_value = ComplianceCheck(
            passed=True,
            region="US",
            rules_applied=[],
            warnings=[],
            restrictions=[],
            required_disclaimers=[],
            metadata={}
        )

        # Mock cache return value (simulating read-through fetch)
        mock_cache.return_value = {
            "price": 150.0,
            "change": 2.5,
            "change_percent": 1.6,
            "volume": 1000000,
            "name": "Apple Inc.",
            "exchange": "NASDAQ",
            "_source_provider": "test_provider",
            "_confidence": 0.95
        }

        result = await search_by_symbol(
            symbol="AAPL",
            market=Market.US,
            depth=AnalysisDepth.QUICK,
            language="en"
        )

        assert result.symbol == "AAPL"
        assert result.cached.price == 150.0
        assert result.cached.source == "test_provider"
        assert result.task.status.name == "PENDING"

        mock_compliance.assert_called_once()
        mock_cache.assert_called_once()


@pytest.mark.asyncio
async def test_search_by_symbol_compliance_failure():
    """Test search_by_symbol when compliance check fails"""

    with patch("fiml.compliance.router.compliance_router.check_compliance", new_callable=AsyncMock) as mock_compliance:
        mock_compliance.return_value = ComplianceCheck(
            passed=False,
            region="US",
            rules_applied=[],
            warnings=[],
            restrictions=["Restricted asset"],
            required_disclaimers=[],
            metadata={}
        )

        result = await search_by_symbol(
            symbol="RESTRICTED",
            market=Market.US,
            depth=AnalysisDepth.QUICK,
            language="en"
        )

        assert result.symbol == "RESTRICTED"
        assert result.cached.source == "compliance_blocked"
        assert "Restricted asset" in result.disclaimer


@pytest.mark.asyncio
async def test_search_by_symbol_fetch_error():
    """Test search_by_symbol when fetching fails"""

    with patch("fiml.compliance.router.compliance_router.check_compliance", new_callable=AsyncMock) as mock_compliance, \
         patch("fiml.cache.manager.cache_manager.get_with_read_through", side_effect=Exception("Fetch failed")):

        mock_compliance.return_value = ComplianceCheck(
            passed=True,
            region="US",
            rules_applied=[],
            warnings=[],
            restrictions=[],
            required_disclaimers=[],
            metadata={}
        )

        result = await search_by_symbol(
            symbol="ERROR",
            market=Market.US,
            depth=AnalysisDepth.QUICK,
            language="en"
        )

        assert result.symbol == "ERROR"
        assert result.cached.source == "error"
        assert "Fetch failed" in result.disclaimer


@pytest.mark.asyncio
async def test_search_by_coin_success():
    """Test search_by_coin with successful data fetch"""

    with patch("fiml.compliance.router.compliance_router.check_compliance", new_callable=AsyncMock) as mock_compliance, \
         patch("fiml.cache.manager.cache_manager.get_with_read_through", new_callable=AsyncMock) as mock_cache, \
         patch("fiml.monitoring.task_registry.task_registry.register"):

        mock_compliance.return_value = ComplianceCheck(
            passed=True,
            region="US",
            rules_applied=[],
            warnings=[],
            restrictions=[],
            required_disclaimers=[],
            metadata={}
        )

        mock_cache.return_value = {
            "price": 50000.0,
            "change": 100.0,
            "change_percent": 0.2,
            "_source_provider": "test_provider",
            "_confidence": 0.95
        }

        result = await search_by_coin(
            symbol="BTC",
            exchange="binance",
            pair="USDT",
            depth=AnalysisDepth.QUICK,
            language="en"
        )

        assert result.symbol == "BTC"
        assert result.cached.price == 50000.0
        assert result.cached.source == "test_provider"


@pytest.mark.asyncio
async def test_track_query_in_session():
    """Test tracking query in session"""

    with patch("fiml.sessions.store.get_session_store", new_callable=AsyncMock) as mock_get_store:
        mock_store = AsyncMock()
        mock_session = MagicMock()

        mock_get_store.return_value = mock_store
        mock_store.get_session.return_value = mock_session

        await track_query_in_session(
            session_id="123e4567-e89b-12d3-a456-426614174000",
            query_type="test",
            parameters={"param": "value"}
        )

        mock_store.get_session.assert_called_once()
        mock_session.add_query.assert_called_once()
        mock_store.update_session.assert_called_once()


def test_calculate_narrative_ttl(mock_asset):
    """Test narrative TTL calculation"""

    # Test crypto (24/7)
    crypto_asset = Asset(symbol="BTC", asset_type=AssetType.CRYPTO)

    # Base TTL
    assert calculate_narrative_ttl(crypto_asset) == 600

    # High volatility
    assert calculate_narrative_ttl(crypto_asset, volatility=15.0) == 180

    # Medium volatility
    assert calculate_narrative_ttl(crypto_asset, volatility=8.0) == 300

    # Test Equity
    # Mock time to be during market hours
    with patch("fiml.mcp.tools.datetime") as mock_datetime:
        mock_now = datetime(2023, 1, 1, 15, 0, tzinfo=timezone.utc) # 15:00 UTC is market hours
        mock_datetime.now.return_value = mock_now

        # Default
        assert calculate_narrative_ttl(mock_asset) == 900

        # High volatility
        assert calculate_narrative_ttl(mock_asset, volatility=5.0) == 300


def test_format_narrative_text(mock_narrative):
    """Test narrative text formatting"""
    text = format_narrative_text(mock_narrative)

    assert "EXECUTIVE SUMMARY" in text
    assert "Test Summary" in text
    assert "TEST SECTION" in text
    assert "Test Content" in text
    assert "KEY INSIGHTS" in text
    assert "Insight 1" in text
    assert "RISK FACTORS" in text
    assert "Risk 1" in text
    assert "DISCLAIMER" in text


def test_format_narrative_markdown(mock_narrative):
    """Test narrative markdown formatting"""
    md = format_narrative_markdown(mock_narrative)

    assert "# Executive Summary" in md
    assert "Test Summary" in md
    assert "## Test Section" in md
    assert "Test Content" in md
    assert "## Key Insights" in md
    assert "- Insight 1" in md
    assert "## Risk Factors" in md
    assert "- Risk 1" in md
    assert "*Test Disclaimer*" in md


def test_truncate_narrative():
    """Test narrative truncation"""
    text = "Short text"
    assert truncate_narrative(text, max_length=100) == text

    long_text = "A" * 100
    truncated = truncate_narrative(long_text, max_length=10)
    assert len(truncated) == 10
    assert truncated.endswith("...")
