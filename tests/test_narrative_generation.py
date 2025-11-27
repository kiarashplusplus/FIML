"""
Comprehensive Tests for Narrative Generation System

Tests all components of the AI narrative generation system including:
- Enhanced Azure client methods
- Template library
- Narrative validator
- Narrative caching
- Batch generation
"""

from unittest.mock import AsyncMock, patch

import pytest

from fiml.core.models import Asset, AssetType
from fiml.llm.azure_client import AzureOpenAIClient
from fiml.narrative.batch import BatchNarrativeGenerator
from fiml.narrative.cache import NarrativeCache
from fiml.narrative.models import Language
from fiml.narrative.templates import TemplateLibrary
from fiml.narrative.validator import NarrativeValidator

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_azure_response():
    """Mock Azure OpenAI API response"""
    return {
        "choices": [
            {
                "message": {
                    "content": "AAPL is trading at $175.50, up $4.25 (2.48%) in the last 24 hours. "
                    "This movement comes on elevated volume. "
                    "This is not financial advice. FIML provides data analysis only."
                }
            }
        ]
    }


@pytest.fixture
def sample_market_data():
    """Sample market data for testing"""
    return {
        "symbol": "AAPL",
        "price": 175.50,
        "change": 4.25,
        "change_percent": 2.48,
        "volume": 75000000,
        "avg_volume": 50000000,
        "week_52_high": 198.23,
        "week_52_low": 124.17,
    }


@pytest.fixture
def sample_technical_data():
    """Sample technical indicators"""
    return {
        "rsi": 65.3,
        "macd": {"macd": 2.45, "signal": 1.92, "histogram": 0.53},
        "bollinger": {"upper": 182.50, "middle": 175.00, "lower": 167.50},
    }


# =============================================================================
# Azure Client Enhanced Methods Tests
# =============================================================================


class TestAzureClientEnhancements:
    """Test enhanced Azure OpenAI client methods"""

    @pytest.mark.asyncio
    async def test_generate_market_summary(self, mock_azure_response, sample_market_data):
        """Test market summary generation"""
        client = AzureOpenAIClient()

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_azure_response

            summary = await client.generate_market_summary(sample_market_data, style="professional")

            assert isinstance(summary, str)
            assert len(summary) > 0
            assert "AAPL" in summary or "175.50" in summary
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_market_summary_fallback(self, sample_market_data):
        """Test fallback when API fails"""
        client = AzureOpenAIClient()

        with patch.object(client, "_make_request", side_effect=Exception("API Error")):
            summary = await client.generate_market_summary(sample_market_data)

            # Should use fallback template
            assert isinstance(summary, str)
            assert "AAPL" in summary
            assert "not financial advice" in summary.lower()

    @pytest.mark.asyncio
    async def test_explain_price_movement(self, mock_azure_response):
        """Test price movement explanation"""
        client = AzureOpenAIClient()

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_azure_response

            explanation = await client.explain_price_movement(
                symbol="AAPL",
                change_pct=2.48,
                volume=75000000,
                news=["Q4 earnings beat estimates"],
            )

            assert isinstance(explanation, str)
            assert len(explanation) > 0
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_interpret_technical_indicators(self, mock_azure_response, sample_technical_data):
        """Test technical indicator interpretation"""
        client = AzureOpenAIClient()

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_azure_response

            interpretation = await client.interpret_technical_indicators(
                rsi=sample_technical_data["rsi"],
                macd=sample_technical_data["macd"],
                bollinger=sample_technical_data["bollinger"],
            )

            assert isinstance(interpretation, str)
            assert len(interpretation) > 0
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_assess_risk_profile(self, mock_azure_response):
        """Test risk profile assessment"""
        client = AzureOpenAIClient()

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_azure_response

            assessment = await client.assess_risk_profile(volatility=0.25, beta=1.15, var=0.05)

            assert isinstance(assessment, str)
            assert len(assessment) > 0
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_compare_assets(self, mock_azure_response):
        """Test asset comparison"""
        client = AzureOpenAIClient()

        asset1 = {"symbol": "AAPL", "pe_ratio": 28.5, "growth": 15.8}
        asset2 = {"symbol": "MSFT", "pe_ratio": 32.1, "growth": 12.3}

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_azure_response

            comparison = await client.compare_assets(asset1, asset2)

            assert isinstance(comparison, str)
            assert len(comparison) > 0
            mock_request.assert_called_once()

    def test_fallback_methods(self):
        """Test all fallback template methods"""
        client = AzureOpenAIClient()

        # Test market summary fallback
        summary = client._fallback_market_summary(
            {"symbol": "AAPL", "price": 175.50, "change": 4.25, "change_percent": 2.48}
        )
        assert "AAPL" in summary
        assert "175.50" in summary
        assert "not financial advice" in summary.lower()

        # Test price movement fallback
        movement = client._fallback_price_movement("AAPL", 2.48, 75000000)
        assert "AAPL" in movement
        assert "2.48" in movement

        # Test technical interpretation fallback
        tech = client._fallback_technical_interpretation(65.3, {"histogram": 0.5}, None)
        assert "RSI" in tech
        assert "MACD" in tech

        # Test risk assessment fallback
        risk = client._fallback_risk_assessment(0.25, 1.25, 0.05)
        assert "volatility" in risk.lower()
        assert "beta" in risk.lower()

        # Test comparison fallback
        comp = client._fallback_comparison(
            {"symbol": "AAPL", "pe_ratio": 28.5},
            {"symbol": "MSFT", "pe_ratio": 32.1},
        )
        assert "AAPL" in comp
        assert "MSFT" in comp


# =============================================================================
# Template Library Tests
# =============================================================================


class TestTemplateLibrary:
    """Test narrative template library"""

    def test_template_initialization(self):
        """Test template library initializes correctly"""
        library = TemplateLibrary()
        assert library.templates is not None
        assert "price_movement" in library.templates
        assert "volume_analysis" in library.templates
        assert "technical_summary" in library.templates

    def test_render_price_movement_english(self):
        """Test price movement template in English"""
        library = TemplateLibrary()
        context = {
            "symbol": "AAPL",
            "price": 175.50,
            "change_pct": 2.48,
            "volume": 75000000,
            "avg_volume": 50000000,
            "week_52_high": 198.23,
            "week_52_low": 124.17,
        }

        text = library.render_template("price_movement", Language.ENGLISH, context)

        assert "AAPL" in text
        assert "175.50" in text or "175.5" in text
        assert "not financial advice" in text.lower()

    def test_render_multilingual_templates(self):
        """Test templates in different languages"""
        library = TemplateLibrary()
        context = {
            "symbol": "AAPL",
            "price": 175.50,
            "change_pct": 2.48,
        }

        # Test multiple languages
        for language in [
            Language.ENGLISH,
            Language.SPANISH,
            Language.FRENCH,
            Language.JAPANESE,
            Language.CHINESE,
        ]:
            text = library.render_template("price_movement", language, context)
            assert len(text) > 0
            assert "AAPL" in text

    def test_context_enrichment(self):
        """Test context enrichment logic"""
        library = TemplateLibrary()

        # Test price movement enrichment
        context = {"change_pct": 5.5, "volume": 100000000, "avg_volume": 50000000}
        enriched = library._enrich_context("price_movement", context)

        assert "direction" in enriched
        assert enriched["direction"] == "up"
        assert "magnitude" in enriched
        assert enriched["magnitude"] == "significant"

    def test_emergency_fallback(self):
        """Test emergency fallback when rendering fails"""
        library = TemplateLibrary()
        fallback = library._emergency_fallback({"symbol": "AAPL"})

        assert "AAPL" in fallback
        assert "not financial advice" in fallback.lower()


# =============================================================================
# Narrative Validator Tests
# =============================================================================


class TestNarrativeValidator:
    """Test narrative quality validator"""

    def test_validator_initialization(self):
        """Test validator initializes correctly"""
        validator = NarrativeValidator()
        assert validator.ADVICE_KEYWORDS is not None
        assert validator.PREDICTIVE_KEYWORDS is not None
        assert validator.REQUIRED_DISCLAIMERS is not None

    def test_check_length(self):
        """Test length validation"""
        validator = NarrativeValidator()

        # Valid length
        assert validator.check_length("A" * 100, 50, 200) is True

        # Too short
        assert validator.check_length("Short", 50, 200) is False

        # Too long
        assert validator.check_length("A" * 300, 50, 200) is False

    def test_check_disclaimer(self):
        """Test disclaimer detection"""
        validator = NarrativeValidator()

        # Has disclaimer
        text_with = "Analysis shows trends. This is not financial advice."
        assert validator.check_disclaimer(text_with) is True

        # No disclaimer
        text_without = "Analysis shows trends."
        assert validator.check_disclaimer(text_without) is False

    def test_check_investment_advice(self):
        """Test investment advice detection"""
        validator = NarrativeValidator()

        # Contains advice
        assert validator.check_investment_advice("You should buy this stock") is True
        assert validator.check_investment_advice("We recommend selling") is True
        assert validator.check_investment_advice("Strong buy rating") is True

        # No advice
        assert validator.check_investment_advice("Price is currently at $100") is False

    def test_check_predictions(self):
        """Test predictive language detection"""
        validator = NarrativeValidator()

        # Has predictions
        predictions = validator.check_predictions(
            "Stock will increase tomorrow and is expected to reach $200"
        )
        assert len(predictions) > 0

        # No predictions
        predictions = validator.check_predictions("Stock is currently at $100")
        assert len(predictions) == 0

    def test_check_readability(self):
        """Test readability scoring"""
        validator = NarrativeValidator()

        simple_text = "The cat sat on the mat. It was a nice day."
        complex_text = "The multifaceted implications of contemporary macroeconomic policies necessitate comprehensive analysis."

        simple_score = validator.check_readability(simple_text)
        complex_score = validator.check_readability(complex_text)

        # Simple text should have higher score
        assert simple_score > complex_score
        assert 0 <= simple_score <= 100

    def test_validate_comprehensive(self):
        """Test comprehensive validation"""
        validator = NarrativeValidator()

        # Valid narrative
        valid_text = (
            "AAPL is currently trading at $175.50, showing a 2.48% increase today. "
            "Volume is elevated at 75 million shares. Technical indicators show bullish momentum. "
            "This is not financial advice. FIML provides data analysis only."
        )

        is_valid, errors, warnings = validator.validate(valid_text)
        assert is_valid is True
        assert len(errors) == 0

        # Invalid narrative (has advice)
        invalid_text = "You should buy AAPL stock now. It will reach $200 soon."

        is_valid, errors, warnings = validator.validate(invalid_text, min_length=10)
        assert is_valid is False
        assert len(errors) > 0

    def test_auto_inject_disclaimer(self):
        """Test automatic disclaimer injection"""
        validator = NarrativeValidator()

        text_without = "AAPL is trading at $175.50."
        text_with = validator.auto_inject_disclaimer(text_without)

        assert "not financial advice" in text_with.lower()
        assert len(text_with) > len(text_without)

        # Should not double-inject
        text_already = "AAPL is trading at $175.50. This is not financial advice."
        text_checked = validator.auto_inject_disclaimer(text_already)
        assert text_checked == text_already

    def test_sanitize_narrative(self):
        """Test narrative sanitization"""
        validator = NarrativeValidator()

        problematic = "You should buy AAPL. It will increase significantly."
        sanitized = validator.sanitize_narrative(problematic)

        # Should remove problematic language
        assert "should buy" not in sanitized.lower()
        assert "will increase" not in sanitized.lower()


# =============================================================================
# Narrative Cache Tests
# =============================================================================


class TestNarrativeCache:
    """Test narrative caching system"""

    @pytest.mark.asyncio
    async def test_cache_initialization(self):
        """Test cache initializes correctly"""
        cache = NarrativeCache()
        assert cache.cache_manager is not None
        assert cache._hit_count == 0
        assert cache._miss_count == 0

    @pytest.mark.asyncio
    async def test_cache_key_generation(self):
        """Test cache key generation"""
        cache = NarrativeCache()

        key1 = cache._generate_cache_key("AAPL", "en", "intermediate")
        key2 = cache._generate_cache_key("AAPL", "en", "intermediate")
        key3 = cache._generate_cache_key("AAPL", "es", "intermediate")

        # Same params should generate same key
        assert key1 == key2

        # Different language should generate different key
        assert key1 != key3

        # Keys should have expected format
        assert "narrative:AAPL:" in key1

    @pytest.mark.asyncio
    async def test_ttl_calculation_equity(self):
        """Test TTL calculation for equity assets"""
        cache = NarrativeCache()

        # Equity during market hours
        equity = Asset(symbol="AAPL", asset_type=AssetType.EQUITY)
        ttl = cache._calculate_ttl(equity, volatility=None)

        assert ttl > 0
        assert ttl <= 3600  # Should be reasonable (max 1 hour on weekends)

        # For volatility testing, use crypto which always considers volatility
        crypto = Asset(symbol="BTC/USD", asset_type=AssetType.CRYPTO)
        # High volatility should reduce TTL
        ttl_high_vol = cache._calculate_ttl(crypto, volatility=5.0)
        ttl_low_vol = cache._calculate_ttl(crypto, volatility=0.5)

        assert ttl_high_vol < ttl_low_vol

    @pytest.mark.asyncio
    async def test_ttl_calculation_crypto(self):
        """Test TTL calculation for crypto assets"""
        cache = NarrativeCache()

        crypto = Asset(symbol="BTC/USD", asset_type=AssetType.CRYPTO)
        ttl = cache._calculate_ttl(crypto, volatility=None)

        # Crypto should have shorter TTL than equity
        assert ttl > 0
        assert ttl <= 600  # 10 minutes max for crypto

    def test_hit_rate_calculation(self):
        """Test cache hit rate calculation"""
        cache = NarrativeCache()

        # No requests yet
        assert cache.get_hit_rate() == 0.0

        # Simulate hits and misses
        cache._hit_count = 80
        cache._miss_count = 20

        hit_rate = cache.get_hit_rate()
        assert hit_rate == 80.0

    def test_get_metrics(self):
        """Test cache metrics retrieval"""
        cache = NarrativeCache()

        cache._hit_count = 80
        cache._miss_count = 20

        metrics = cache.get_metrics()

        assert metrics["hit_count"] == 80
        assert metrics["miss_count"] == 20
        assert metrics["hit_rate"] == 80.0
        assert metrics["total_requests"] == 100


# =============================================================================
# Batch Narrative Generator Tests
# =============================================================================


class TestBatchNarrativeGenerator:
    """Test batch narrative generation"""

    def test_generator_initialization(self):
        """Test batch generator initializes correctly"""
        generator = BatchNarrativeGenerator()

        assert generator.narrative_generator is not None
        assert generator.POPULAR_SYMBOLS is not None
        assert len(generator.POPULAR_SYMBOLS) > 0

    def test_determine_asset_type(self):
        """Test asset type determination"""
        generator = BatchNarrativeGenerator()

        assert generator._determine_asset_type("AAPL") == "equity"
        assert generator._determine_asset_type("BTC/USD") == "crypto"
        assert generator._determine_asset_type("SPY") == "index"

    def test_is_market_open_soon(self):
        """Test market hours detection"""
        generator = BatchNarrativeGenerator()

        # This is time-dependent, just verify it returns boolean
        result = generator._is_market_open_soon()
        assert isinstance(result, bool)

    def test_get_metrics(self):
        """Test batch generator metrics"""
        generator = BatchNarrativeGenerator()

        # Simulate some generations
        generator._generation_count = 90
        generator._error_count = 10

        metrics = generator.get_metrics()

        assert metrics["total_generated"] == 90
        assert metrics["total_errors"] == 10
        assert metrics["success_rate"] == 90.0


# =============================================================================
# Integration Tests
# =============================================================================


class TestNarrativeSystemIntegration:
    """Integration tests for complete narrative system"""

    @pytest.mark.asyncio
    async def test_end_to_end_narrative_generation(self, mock_azure_response):
        """Test complete narrative generation flow"""
        # This would test the entire pipeline:
        # 1. Generate narrative via Azure client
        # 2. Validate narrative
        # 3. Cache narrative
        # 4. Retrieve from cache

        client = AzureOpenAIClient()
        validator = NarrativeValidator()
        NarrativeCache()

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_azure_response

            # Generate
            narrative = await client.generate_market_summary(
                {"symbol": "AAPL", "price": 175.50, "change_percent": 2.48}
            )

            # Validate
            is_valid, errors, warnings = validator.validate(narrative)
            if not is_valid:
                narrative = validator.auto_inject_disclaimer(narrative)

            # Should be valid now
            is_valid, errors, warnings = validator.validate(narrative)
            assert is_valid is True

    def test_template_fallback_on_api_failure(self, sample_market_data):
        """Test that templates work when API fails"""
        library = TemplateLibrary()

        # Generate using template
        narrative = library.render_template("price_movement", Language.ENGLISH, sample_market_data)

        # Validate generated text
        validator = NarrativeValidator()
        is_valid, errors, warnings = validator.validate(narrative, min_length=10)

        assert is_valid is True
        assert "AAPL" in narrative

    def test_multilingual_support(self):
        """Test multilingual narrative generation"""
        library = TemplateLibrary()
        validator = NarrativeValidator()

        context = {"symbol": "AAPL", "price": 175.50, "change_pct": 2.48}

        for language in [Language.ENGLISH, Language.SPANISH, Language.FRENCH]:
            narrative = library.render_template("price_movement", language, context)

            # All languages should produce valid narratives
            is_valid, errors, warnings = validator.validate(narrative, min_length=10)
            assert is_valid is True, f"Failed for {language}: {errors}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
