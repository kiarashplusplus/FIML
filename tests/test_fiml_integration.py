"""
Tests for FIML Educational Data Adapter integration.

These tests verify that the adapter correctly integrates with
FIML MCP tools and provides educational data for both bot and mobile app.
"""

import pytest

from fiml.bot.education.fiml_adapter import (
    FIMLEducationalDataAdapter,
    get_fiml_data_adapter,
)
from fiml.core.models import AssetType


class TestFIMLEducationalDataAdapter:
    """Tests for FIMLEducationalDataAdapter"""

    @pytest.fixture
    def adapter(self):
        """Create adapter instance"""
        return FIMLEducationalDataAdapter()

    def test_initialization(self, adapter):
        """Test adapter initializes correctly"""
        assert adapter is not None

    def test_detect_asset_type_stock(self, adapter):
        """Test detecting stock symbols"""
        assert adapter._detect_asset_type("AAPL") == AssetType.EQUITY
        assert adapter._detect_asset_type("TSLA") == AssetType.EQUITY
        assert adapter._detect_asset_type("MSFT") == AssetType.EQUITY
        assert adapter._detect_asset_type("UNKNOWN") == AssetType.EQUITY

    def test_detect_asset_type_crypto(self, adapter):
        """Test detecting crypto symbols"""
        assert adapter._detect_asset_type("BTC") == AssetType.CRYPTO
        assert adapter._detect_asset_type("ETH") == AssetType.CRYPTO
        assert adapter._detect_asset_type("SOL") == AssetType.CRYPTO
        assert adapter._detect_asset_type("BTC/USDT") == AssetType.CRYPTO

    def test_explain_price_movement(self, adapter):
        """Test price movement explanations"""
        # Minimal movement
        explanation = adapter.explain_price_movement(0.3)
        assert "Minimal" in explanation
        assert "up" in explanation

        # Moderate movement
        explanation = adapter.explain_price_movement(-1.5)
        assert "Moderate" in explanation
        assert "down" in explanation

        # Significant movement
        explanation = adapter.explain_price_movement(3.5)
        assert "Significant" in explanation

        # Exceptional movement
        explanation = adapter.explain_price_movement(-7.0)
        assert "Exceptional" in explanation

    def test_explain_volume(self, adapter):
        """Test volume explanations"""
        # Low volume
        explanation = adapter.explain_volume(40000, 100000)
        assert "low interest" in explanation.lower()

        # Normal volume
        explanation = adapter.explain_volume(100000, 100000)
        assert "normal" in explanation.lower()

        # High volume
        explanation = adapter.explain_volume(250000, 100000)
        assert "high interest" in explanation.lower() or "elevated" in explanation.lower()

    def test_explain_pe_ratio(self, adapter):
        """Test P/E ratio explanations"""
        assert "Negative" in adapter.explain_pe_ratio(-5)
        assert "Low" in adapter.explain_pe_ratio(10)
        assert "Moderate" in adapter.explain_pe_ratio(20)
        assert "High" in adapter.explain_pe_ratio(35)
        assert "Very high" in adapter.explain_pe_ratio(50)

    def test_explain_market_cap(self, adapter):
        """Test market cap explanations"""
        assert "Micro-cap" in adapter.explain_market_cap(100_000_000)
        assert "Small-cap" in adapter.explain_market_cap(1_000_000_000)
        assert "Mid-cap" in adapter.explain_market_cap(5_000_000_000)
        assert "Large-cap" in adapter.explain_market_cap(50_000_000_000)
        assert "Mega-cap" in adapter.explain_market_cap(300_000_000_000)

    def test_get_template_snapshot_stock(self, adapter):
        """Test fallback template for stocks"""
        snapshot = adapter._get_template_snapshot("AAPL")
        
        assert snapshot["symbol"] == "AAPL"
        assert snapshot["asset_type"] == "stock"
        assert snapshot["is_fallback"] is True
        assert "price" in snapshot
        assert "volume" in snapshot
        assert "fundamentals" in snapshot
        assert "disclaimer" in snapshot

    def test_get_template_snapshot_crypto(self, adapter):
        """Test fallback template for crypto"""
        snapshot = adapter._get_template_snapshot("BTC")
        
        assert snapshot["symbol"] == "BTC"
        assert snapshot["asset_type"] == "crypto"
        assert snapshot["is_fallback"] is True
        assert "crypto_metrics" in snapshot

    @pytest.mark.asyncio
    async def test_format_for_lesson(self, adapter):
        """Test formatting data for lesson display"""
        data = {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "price": {"current": 150.0, "change_percent": 2.5, "explanation": "Test"},
            "volume": {"current": 50000000, "interpretation": "Normal"},
            "fundamentals": {"pe_ratio": 25, "market_cap": "2.5T", "explanation": "Test"},
            "disclaimer": "Test disclaimer",
        }
        
        formatted = await adapter.format_for_lesson(data)
        
        assert "AAPL" in formatted
        assert "Apple Inc." in formatted
        assert "$150.00" in formatted
        assert "2.50%" in formatted

    @pytest.mark.asyncio
    async def test_format_for_quiz(self, adapter):
        """Test formatting data for quiz display"""
        data = {
            "symbol": "TSLA",
            "price": {"current": 200.0, "change_percent": -1.5},
            "volume": {"current": 30000000},
        }
        
        formatted = await adapter.format_for_quiz(data)
        
        assert "TSLA" in formatted
        assert "$200.00" in formatted
        assert "-1.50%" in formatted

    @pytest.mark.asyncio
    async def test_format_for_mentor(self, adapter):
        """Test formatting data for mentor context"""
        data = {
            "symbol": "MSFT",
            "price": {"current": 350.0, "change_percent": 1.0, "explanation": "Moderate up"},
        }
        
        formatted = await adapter.format_for_mentor(data, "What is MSFT?")
        
        assert "MSFT" in formatted
        assert "$350.00" in formatted

    def test_create_chart_description(self, adapter):
        """Test chart description generation"""
        # Upward trend
        data = {"price": {"current": 100, "change_percent": 3.0}}
        desc = adapter.create_chart_description(data)
        assert "upward" in desc
        assert "green" in desc

        # Downward trend
        data = {"price": {"current": 100, "change_percent": -3.0}}
        desc = adapter.create_chart_description(data)
        assert "downward" in desc
        assert "red" in desc


class TestFIMLDataAdapterSingleton:
    """Tests for singleton accessor"""

    def test_get_fiml_data_adapter_returns_same_instance(self):
        """Test that singleton returns same instance"""
        adapter1 = get_fiml_data_adapter()
        adapter2 = get_fiml_data_adapter()
        
        assert adapter1 is adapter2

    def test_get_fiml_data_adapter_returns_valid_adapter(self):
        """Test that singleton returns valid adapter"""
        adapter = get_fiml_data_adapter()

        assert isinstance(adapter, FIMLEducationalDataAdapter)


class TestIntentClassifierDSL:
    """Tests for DSL query detection in IntentClassifier"""

    @pytest.fixture
    def classifier(self):
        """Create intent classifier instance"""
        from fiml.bot.core.gateway import IntentClassifier
        return IntentClassifier()

    def test_is_dsl_query_evaluate(self, classifier):
        """Test DSL query detection for EVALUATE"""
        assert classifier._is_dsl_query("EVALUATE AAPL: PRICE, VOLUME")
        assert classifier._is_dsl_query("EVALUATE TSLA: PRICE")
        assert classifier._is_dsl_query("evaluate aapl: price")  # Case insensitive

    def test_is_dsl_query_compare(self, classifier):
        """Test DSL query detection for COMPARE"""
        assert classifier._is_dsl_query("COMPARE AAPL, MSFT: PE_RATIO")
        assert classifier._is_dsl_query("COMPARE BTC, ETH: PRICE(30d)")

    def test_is_dsl_query_correlate(self, classifier):
        """Test DSL query detection for CORRELATE"""
        assert classifier._is_dsl_query("CORRELATE BTC, ETH: PRICE(90d)")

    def test_is_dsl_query_screen(self, classifier):
        """Test DSL query detection for SCREEN"""
        assert classifier._is_dsl_query("SCREEN SECTOR=TECH: PE_RATIO")

    def test_is_dsl_query_false_for_normal_text(self, classifier):
        """Test that normal text is not detected as DSL"""
        assert not classifier._is_dsl_query("What is a P/E ratio?")
        assert not classifier._is_dsl_query("Show me AAPL price")
        assert not classifier._is_dsl_query("Hello, how are you?")


class TestLessonEngine:
    """Tests for LessonContentEngine dynamic lesson loading"""

    @pytest.fixture
    def engine(self):
        """Create lesson engine instance with default path"""
        from fiml.bot.education.lesson_engine import LessonContentEngine
        return LessonContentEngine()

    @pytest.mark.asyncio
    async def test_list_lessons_returns_list(self, engine):
        """Test that list_lessons returns a list"""
        lessons = await engine.list_lessons()
        assert isinstance(lessons, list)

    @pytest.mark.asyncio
    async def test_list_lessons_has_required_fields(self, engine):
        """Test that lessons have required metadata fields"""
        lessons = await engine.list_lessons()
        if lessons:  # Only test if lessons exist
            lesson = lessons[0]
            assert "id" in lesson
            assert "title" in lesson
            assert "difficulty" in lesson
            assert "category" in lesson

    @pytest.mark.asyncio
    async def test_list_lessons_loads_from_content_dir(self, engine):
        """Test that lessons are loaded from the content directory"""
        lessons = await engine.list_lessons()
        # Content directory has 20+ lessons
        assert len(lessons) >= 15
