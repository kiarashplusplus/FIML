"""
Tests for Narrative Generation System

Comprehensive test suite covering:
- Data models validation
- Prompt template system
- Narrative generation
- Multi-language support
- Expertise level adaptation
- Quality validation
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from fiml.llm.azure_client import AzureOpenAIClient
from fiml.narrative.generator import NarrativeGenerator
from fiml.narrative.models import (
    ExpertiseLevel,
    Language,
    Narrative,
    NarrativeContext,
    NarrativePreferences,
    NarrativeSection,
    NarrativeType,
)
from fiml.narrative.prompts import PromptTemplateLibrary, prompt_library

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_azure_client():
    """Mock Azure OpenAI client"""
    client = MagicMock(spec=AzureOpenAIClient)
    client._make_request = AsyncMock()
    return client


@pytest.fixture
def sample_price_data():
    """Sample price data for testing"""
    return {
        "price": 175.50,
        "change": 4.25,
        "change_percent": 2.48,
        "volume": 75000000,
        "avg_volume": 50000000,
        "market_cap": 2750000000000,
        "week_52_high": 198.23,
        "week_52_low": 124.17,
        "day_high": 176.80,
        "day_low": 173.90,
        "beta": 1.15,
        "volatility": 0.25,
    }


@pytest.fixture
def sample_technical_data():
    """Sample technical analysis data"""
    return {
        "rsi": 65.3,
        "macd": {"macd": 2.45, "signal": 1.92, "histogram": 0.53},
        "ma_50": 170.25,
        "ma_200": 165.80,
        "current_price": 175.50,
        "stochastic": {"k": 72.5, "d": 68.3},
        "bollinger": {"upper": 182.50, "middle": 175.00, "lower": 167.50},
        "atr": 3.85,
        "ma_50_position": "above",
        "ma_200_position": "above",
    }


@pytest.fixture
def sample_fundamental_data():
    """Sample fundamental analysis data"""
    return {
        "pe_ratio": 28.5,
        "industry_pe": 25.3,
        "sector_pe": 27.1,
        "sp500_pe": 21.5,
        "pb_ratio": 6.8,
        "peg_ratio": 1.8,
        "ev_ebitda": 18.2,
        "market_cap": 2750000000000,
        "revenue": 394000000000,
        "net_margin": 25.3,
        "roe": 147.5,
        "debt_equity": 1.73,
        "eps_growth": 15.8,
        "revenue_growth": 8.1,
        "profit_margin": 25.3,
    }


@pytest.fixture
def sample_sentiment_data():
    """Sample sentiment analysis data"""
    return {
        "overall_score": 0.65,
        "news_sentiment": 0.72,
        "social_sentiment": 0.58,
        "trend": "positive",
        "headlines": [
            "Company reports strong quarterly earnings",
            "New product launch exceeds expectations",
            "Analyst upgrades stock to Buy",
            "Market share gains in key segment",
            "Innovation pipeline looking robust",
        ],
        "trending_topics": [
            "earnings",
            "innovation",
            "market share",
            "growth",
            "AI integration",
        ],
    }


@pytest.fixture
def sample_risk_data():
    """Sample risk analysis data"""
    return {
        "volatility_30d": 25.3,
        "beta": 1.15,
        "sharpe_ratio": 1.42,
        "max_drawdown": -18.5,
        "var_1d": -2.8,
        "var_10d": -8.9,
        "sp500_correlation": 0.82,
    }


@pytest.fixture
def sample_context(
    sample_price_data,
    sample_technical_data,
    sample_fundamental_data,
    sample_sentiment_data,
    sample_risk_data,
):
    """Sample narrative context"""
    return NarrativeContext(
        asset_symbol="AAPL",
        asset_name="Apple Inc.",
        asset_type="equity",
        market="US",
        price_data=sample_price_data,
        technical_data=sample_technical_data,
        fundamental_data=sample_fundamental_data,
        sentiment_data=sample_sentiment_data,
        risk_data=sample_risk_data,
        region="US",
        data_sources=["yahoo_finance", "alpha_vantage", "newsapi"],
    )


@pytest.fixture
def mock_llm_response():
    """Mock LLM response"""
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "This is a test narrative response from the LLM.",
                },
                "finish_reason": "stop",
            }
        ]
    }


# ============================================================================
# Model Tests
# ============================================================================


class TestNarrativeModels:
    """Test narrative data models"""

    def test_narrative_section_creation(self):
        """Test NarrativeSection model creation"""
        section = NarrativeSection(
            title="Test Section",
            content="This is test content for the narrative section.",
            section_type=NarrativeType.MARKET_CONTEXT,
            confidence=0.95,
        )

        assert section.title == "Test Section"
        assert section.section_type == NarrativeType.MARKET_CONTEXT
        assert section.confidence == 0.95
        assert section.word_count > 0

    def test_narrative_section_content_validation(self):
        """Test content length validation"""
        with pytest.raises(ValueError, match="at least 10 characters"):
            NarrativeSection(
                title="Test",
                content="Short",
                section_type=NarrativeType.TECHNICAL,
            )

    def test_narrative_creation(self):
        """Test Narrative model creation"""
        sections = [
            NarrativeSection(
                title="Market Context",
                content="Market is showing positive momentum today.",
                section_type=NarrativeType.MARKET_CONTEXT,
            )
        ]

        narrative = Narrative(
            summary="Overall market analysis shows positive trends with strong momentum and good volume indicators.",
            sections=sections,
            key_insights=["Positive momentum", "Strong volume"],
            risk_factors=["High volatility"],
            disclaimer="This is not financial advice.",
            language=Language.ENGLISH,
            expertise_level=ExpertiseLevel.INTERMEDIATE,
        )

        assert narrative.summary is not None
        assert len(narrative.sections) == 1
        assert len(narrative.key_insights) == 2
        assert narrative.total_word_count > 0

    def test_narrative_get_section(self):
        """Test getting specific section by type"""
        sections = [
            NarrativeSection(
                title="Market Context",
                content="Market context content here.",
                section_type=NarrativeType.MARKET_CONTEXT,
            ),
            NarrativeSection(
                title="Technical",
                content="Technical analysis content here.",
                section_type=NarrativeType.TECHNICAL,
            ),
        ]

        narrative = Narrative(
            summary="This is a comprehensive test summary of the market analysis showing key trends and indicators.",
            sections=sections,
            disclaimer="This is not financial advice and is for informational purposes only.",
        )

        technical_section = narrative.get_section(NarrativeType.TECHNICAL)
        assert technical_section is not None
        assert technical_section.title == "Technical"

    def test_narrative_context_symbol_validation(self):
        """Test asset symbol normalization"""
        context = NarrativeContext(
            asset_symbol="  aapl  ",
            asset_type="equity",
            price_data={"price": 100},
        )

        assert context.asset_symbol == "AAPL"

    def test_expertise_level_enum(self):
        """Test expertise level enumeration"""
        assert ExpertiseLevel.BEGINNER.value == "beginner"
        assert ExpertiseLevel.INTERMEDIATE.value == "intermediate"
        assert ExpertiseLevel.ADVANCED.value == "advanced"
        assert ExpertiseLevel.QUANT.value == "quant"

    def test_language_enum(self):
        """Test language enumeration"""
        assert Language.ENGLISH.value == "en"
        assert Language.SPANISH.value == "es"
        assert Language.FRENCH.value == "fr"
        assert Language.JAPANESE.value == "ja"
        assert Language.CHINESE.value == "zh"
        assert Language.FARSI.value == "fa"


# ============================================================================
# Prompt Template Tests
# ============================================================================


class TestPromptTemplates:
    """Test prompt template system"""

    def test_prompt_library_initialization(self):
        """Test prompt library initializes correctly"""
        library = PromptTemplateLibrary()
        assert library.templates is not None
        assert len(library.templates) > 0

    def test_get_market_context_template(self):
        """Test retrieving market context template"""
        template = prompt_library.get_template(
            NarrativeType.MARKET_CONTEXT,
            ExpertiseLevel.INTERMEDIATE,
            Language.ENGLISH,
        )

        assert "system" in template
        assert "user" in template
        assert len(template["system"]) > 0
        assert len(template["user"]) > 0

    def test_get_technical_template(self):
        """Test retrieving technical analysis template"""
        template = prompt_library.get_template(
            NarrativeType.TECHNICAL,
            ExpertiseLevel.BEGINNER,
            Language.ENGLISH,
        )

        assert "system" in template
        assert "RSI" in template["user"] or "technical" in template["user"].lower()

    def test_template_fallback_to_english(self):
        """Test template falls back to English if language not available"""
        template = prompt_library.get_template(
            NarrativeType.MARKET_CONTEXT,
            ExpertiseLevel.INTERMEDIATE,
            Language.GERMAN,  # May not have German templates
        )

        assert template is not None
        assert "system" in template

    def test_get_language_name(self):
        """Test language name retrieval"""
        assert prompt_library.get_language_name(Language.ENGLISH) == "English"
        assert prompt_library.get_language_name(Language.SPANISH) == "Spanish"
        assert prompt_library.get_language_name(Language.JAPANESE) == "Japanese"


# ============================================================================
# Narrative Generator Tests
# ============================================================================


class TestNarrativeGenerator:
    """Test narrative generation functionality"""

    def test_generator_initialization(self, mock_azure_client):
        """Test generator initializes correctly"""
        generator = NarrativeGenerator(azure_client=mock_azure_client)

        assert generator.azure_client is not None
        assert generator.disclaimer_generator is not None
        assert generator.prompt_library is not None

    @pytest.mark.asyncio
    async def test_generate_market_context(
        self, mock_azure_client, mock_llm_response, sample_price_data
    ):
        """Test market context generation"""
        mock_azure_client._make_request.return_value = mock_llm_response

        generator = NarrativeGenerator(azure_client=mock_azure_client)
        preferences = NarrativePreferences()

        section = await generator._generate_market_context(
            "AAPL",
            "Apple Inc.",
            sample_price_data,
            preferences,
        )

        assert section is not None
        assert section.section_type == NarrativeType.MARKET_CONTEXT
        assert section.title == "Market Context"
        assert len(section.content) > 0
        mock_azure_client._make_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_technical_narrative(
        self, mock_azure_client, mock_llm_response, sample_technical_data
    ):
        """Test technical narrative generation"""
        mock_azure_client._make_request.return_value = mock_llm_response

        generator = NarrativeGenerator(azure_client=mock_azure_client)
        preferences = NarrativePreferences()

        section = await generator._generate_technical_narrative(
            "AAPL",
            sample_technical_data,
            preferences,
        )

        assert section is not None
        assert section.section_type == NarrativeType.TECHNICAL
        assert section.title == "Technical Analysis"

    @pytest.mark.asyncio
    async def test_generate_fundamental_narrative(
        self, mock_azure_client, mock_llm_response, sample_fundamental_data
    ):
        """Test fundamental narrative generation"""
        mock_azure_client._make_request.return_value = mock_llm_response

        generator = NarrativeGenerator(azure_client=mock_azure_client)
        preferences = NarrativePreferences()

        section = await generator._generate_fundamental_narrative(
            "AAPL",
            "Apple Inc.",
            sample_fundamental_data,
            preferences,
        )

        assert section is not None
        assert section.section_type == NarrativeType.FUNDAMENTAL

    @pytest.mark.asyncio
    async def test_generate_sentiment_narrative(
        self, mock_azure_client, mock_llm_response, sample_sentiment_data
    ):
        """Test sentiment narrative generation"""
        mock_azure_client._make_request.return_value = mock_llm_response

        generator = NarrativeGenerator(azure_client=mock_azure_client)
        preferences = NarrativePreferences()

        section = await generator._generate_sentiment_narrative(
            "AAPL",
            sample_sentiment_data,
            preferences,
        )

        assert section is not None
        assert section.section_type == NarrativeType.SENTIMENT

    @pytest.mark.asyncio
    async def test_generate_risk_narrative(
        self, mock_azure_client, mock_llm_response, sample_risk_data
    ):
        """Test risk narrative generation"""
        mock_azure_client._make_request.return_value = mock_llm_response

        generator = NarrativeGenerator(azure_client=mock_azure_client)
        preferences = NarrativePreferences()

        section = await generator._generate_risk_narrative(
            "AAPL",
            sample_risk_data,
            preferences,
        )

        assert section is not None
        assert section.section_type == NarrativeType.RISK

    @pytest.mark.asyncio
    async def test_generate_full_narrative(
        self, mock_azure_client, mock_llm_response, sample_context
    ):
        """Test full narrative generation"""
        mock_azure_client._make_request.return_value = mock_llm_response

        generator = NarrativeGenerator(azure_client=mock_azure_client)

        narrative = await generator.generate_narrative(sample_context)

        assert narrative is not None
        assert narrative.summary is not None
        assert len(narrative.sections) > 0
        assert narrative.disclaimer is not None
        assert narrative.language == Language.ENGLISH
        assert narrative.expertise_level == ExpertiseLevel.INTERMEDIATE

    @pytest.mark.asyncio
    async def test_generate_narrative_with_different_expertise_levels(
        self, mock_azure_client, mock_llm_response, sample_context
    ):
        """Test narrative generation for different expertise levels"""
        mock_azure_client._make_request.return_value = mock_llm_response

        generator = NarrativeGenerator(azure_client=mock_azure_client)

        for expertise_level in ExpertiseLevel:
            sample_context.preferences.expertise_level = expertise_level

            narrative = await generator.generate_narrative(sample_context)

            assert narrative.expertise_level == expertise_level
            assert len(narrative.sections) > 0

    @pytest.mark.asyncio
    async def test_extract_key_insights(self, mock_azure_client, sample_context):
        """Test key insights extraction"""
        insights_response = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            [
                                "Strong positive momentum",
                                "High trading volume",
                                "Positive market sentiment",
                            ]
                        )
                    }
                }
            ]
        }
        mock_azure_client._make_request.return_value = insights_response

        generator = NarrativeGenerator(azure_client=mock_azure_client)

        sections = [
            NarrativeSection(
                title="Test",
                content="Test content here.",
                section_type=NarrativeType.MARKET_CONTEXT,
            )
        ]

        insights = await generator._extract_key_insights(sample_context, sections)

        assert isinstance(insights, list)
        assert len(insights) <= 5

    @pytest.mark.asyncio
    async def test_extract_insights_fallback(self, mock_azure_client, sample_context):
        """Test insights extraction fallback when LLM fails"""
        mock_azure_client._make_request.side_effect = Exception("LLM error")

        generator = NarrativeGenerator(azure_client=mock_azure_client)

        sections = []
        insights = await generator._extract_key_insights(sample_context, sections)

        # Should use fallback method
        assert isinstance(insights, list)

    def test_extract_risk_factors(self, mock_azure_client, sample_context):
        """Test risk factor extraction"""
        generator = NarrativeGenerator(azure_client=mock_azure_client)

        risk_factors = generator._extract_risk_factors(sample_context, [])

        assert isinstance(risk_factors, list)
        assert len(risk_factors) <= 5

    def test_generate_disclaimer(self, mock_azure_client, sample_context):
        """Test disclaimer generation"""
        generator = NarrativeGenerator(azure_client=mock_azure_client)

        disclaimer = generator._generate_disclaimer(sample_context)

        assert disclaimer is not None
        assert len(disclaimer) > 10
        assert "financial advice" in disclaimer.lower() or "informational" in disclaimer.lower()

    def test_calculate_readability(self, mock_azure_client):
        """Test readability calculation"""
        generator = NarrativeGenerator(azure_client=mock_azure_client)

        simple_text = "The cat sat on the mat. It was a nice day."
        complex_text = (
            "The comprehensive multifaceted analysis demonstrates "
            "significant interdependencies between macroeconomic variables."
        )

        simple_score = generator._calculate_readability(simple_text)
        complex_score = generator._calculate_readability(complex_text)

        assert 0 <= simple_score <= 100
        assert 0 <= complex_score <= 100
        # Simple text should have higher readability score
        assert simple_score > complex_score

    def test_count_syllables(self, mock_azure_client):
        """Test syllable counting"""
        generator = NarrativeGenerator(azure_client=mock_azure_client)

        assert generator._count_syllables("cat") == 1
        assert generator._count_syllables("hello") == 2
        assert generator._count_syllables("beautiful") >= 2

    def test_validate_narrative_quality(self, mock_azure_client):
        """Test narrative quality validation"""
        generator = NarrativeGenerator(azure_client=mock_azure_client)

        narrative = Narrative(
            summary="This is a comprehensive analysis of the asset showing strong performance.",
            sections=[
                NarrativeSection(
                    title="Market Context",
                    content="The market shows positive momentum with strong volume.",
                    section_type=NarrativeType.MARKET_CONTEXT,
                    confidence=0.95,
                    readability_score=65.0,
                )
            ],
            key_insights=["Strong momentum", "High volume"],
            risk_factors=["Volatility"],
            disclaimer="This is not financial advice.",
        )

        context = NarrativeContext(
            asset_symbol="AAPL",
            asset_type="equity",
            price_data={"price": 100},
            preferences=NarrativePreferences(),
        )

        quality_metrics = generator._validate_narrative_quality(narrative, context)

        assert 0 <= quality_metrics.overall_quality <= 1
        assert 0 <= quality_metrics.coherence_score <= 1
        assert 0 <= quality_metrics.completeness_score <= 1
        assert 0 <= quality_metrics.accuracy_score <= 1
        assert quality_metrics.compliance_score == 1.0  # Has disclaimer


class TestNarrativePreferences:
    """Test narrative preferences"""

    def test_default_preferences(self):
        """Test default preference values"""
        prefs = NarrativePreferences()

        assert prefs.language == Language.ENGLISH
        assert prefs.expertise_level == ExpertiseLevel.INTERMEDIATE
        assert prefs.include_technical is True
        assert prefs.include_fundamental is True
        assert prefs.include_sentiment is True
        assert prefs.include_risk is True

    def test_custom_preferences(self):
        """Test custom preference configuration"""
        prefs = NarrativePreferences(
            language=Language.SPANISH,
            expertise_level=ExpertiseLevel.BEGINNER,
            include_technical=False,
            max_length_chars=1000,
        )

        assert prefs.language == Language.SPANISH
        assert prefs.expertise_level == ExpertiseLevel.BEGINNER
        assert prefs.include_technical is False
        assert prefs.max_length_chars == 1000


class TestErrorHandling:
    """Test error handling in narrative generation"""

    @pytest.mark.asyncio
    async def test_market_context_generation_failure(self, mock_azure_client, sample_price_data):
        """Test handling of market context generation failure"""
        mock_azure_client._make_request.side_effect = Exception("API Error")

        generator = NarrativeGenerator(azure_client=mock_azure_client)
        preferences = NarrativePreferences()

        section = await generator._generate_market_context(
            "AAPL",
            "Apple Inc.",
            sample_price_data,
            preferences,
        )

        # Should return None on error
        assert section is None

    @pytest.mark.asyncio
    async def test_narrative_generation_with_minimal_data(
        self, mock_azure_client, mock_llm_response
    ):
        """Test narrative generation with minimal data"""
        mock_azure_client._make_request.return_value = mock_llm_response

        generator = NarrativeGenerator(azure_client=mock_azure_client)

        # Minimal context with only price data
        context = NarrativeContext(
            asset_symbol="TEST",
            asset_type="equity",
            price_data={"price": 100, "change_percent": 1.5},
        )

        narrative = await generator.generate_narrative(context)

        assert narrative is not None
        assert narrative.summary is not None
        assert narrative.disclaimer is not None

    @pytest.mark.asyncio
    async def test_technical_narrative_generation_failure(
        self, mock_azure_client, sample_technical_data
    ):
        """Test handling of technical narrative generation failure"""
        mock_azure_client._make_request.side_effect = Exception("API Error")

        generator = NarrativeGenerator(azure_client=mock_azure_client)
        preferences = NarrativePreferences()

        section = await generator._generate_technical_narrative(
            "AAPL",
            sample_technical_data,
            preferences,
        )

        assert section is None

    @pytest.mark.asyncio
    async def test_fundamental_narrative_generation_failure(
        self, mock_azure_client, sample_fundamental_data
    ):
        """Test handling of fundamental narrative generation failure"""
        mock_azure_client._make_request.side_effect = Exception("API Error")

        generator = NarrativeGenerator(azure_client=mock_azure_client)
        preferences = NarrativePreferences()

        section = await generator._generate_fundamental_narrative(
            "AAPL",
            "Apple Inc.",
            sample_fundamental_data,
            preferences,
        )

        assert section is None

    @pytest.mark.asyncio
    async def test_sentiment_narrative_generation_failure(
        self, mock_azure_client, sample_sentiment_data
    ):
        """Test handling of sentiment narrative generation failure"""
        mock_azure_client._make_request.side_effect = Exception("API Error")

        generator = NarrativeGenerator(azure_client=mock_azure_client)
        preferences = NarrativePreferences()

        section = await generator._generate_sentiment_narrative(
            "AAPL",
            sample_sentiment_data,
            preferences,
        )

        assert section is None

    @pytest.mark.asyncio
    async def test_risk_narrative_generation_failure(self, mock_azure_client, sample_risk_data):
        """Test handling of risk narrative generation failure"""
        mock_azure_client._make_request.side_effect = Exception("API Error")

        generator = NarrativeGenerator(azure_client=mock_azure_client)
        preferences = NarrativePreferences()

        section = await generator._generate_risk_narrative(
            "AAPL",
            sample_risk_data,
            preferences,
        )

        assert section is None

    @pytest.mark.asyncio
    async def test_summary_generation_failure(self, mock_azure_client, sample_context):
        """Test handling of summary generation failure"""
        mock_azure_client._make_request.side_effect = Exception("API Error")

        generator = NarrativeGenerator(azure_client=mock_azure_client)

        sections = []
        insights = ["Test insight"]

        summary = await generator._generate_executive_summary(sample_context, sections, insights)

        # Should return fallback summary
        assert summary is not None
        assert "AAPL" in summary


class TestAdditionalCoverage:
    """Additional tests for edge cases and full coverage"""

    def test_narrative_add_section(self):
        """Test adding section to narrative"""
        narrative = Narrative(
            summary="This is a comprehensive test summary of the market analysis showing key trends.",
            disclaimer="This is not financial advice.",
        )

        initial_count = narrative.total_word_count

        new_section = NarrativeSection(
            title="New Section",
            content="This is new content for the narrative.",
            section_type=NarrativeType.MARKET_CONTEXT,
        )

        narrative.add_section(new_section)

        assert len(narrative.sections) == 1
        assert narrative.total_word_count > initial_count

    def test_narrative_section_validation_max_length(self):
        """Test narrative section max length validation"""
        long_content = "a " * 3000  # Exceeds 5000 character limit

        from pydantic_core import ValidationError

        with pytest.raises(ValidationError):
            NarrativeSection(
                title="Test",
                content=long_content,
                section_type=NarrativeType.TECHNICAL,
            )

    def test_narrative_context_default_preferences(self):
        """Test narrative context with default preferences"""
        context = NarrativeContext(
            asset_symbol="AAPL",
            asset_type="equity",
            price_data={"price": 100},
        )

        assert context.preferences.language == Language.ENGLISH
        assert context.preferences.expertise_level == ExpertiseLevel.INTERMEDIATE

    def test_narrative_quality_metrics_with_issues(self, mock_azure_client):
        """Test quality validation with issues detected"""
        generator = NarrativeGenerator(azure_client=mock_azure_client)

        # Narrative with empty sections when sections are expected
        narrative = Narrative(
            summary="This is a summary that meets the minimum character length requirements.",
            sections=[],
            disclaimer="This is not financial advice.",
        )

        context = NarrativeContext(
            asset_symbol="TEST",
            asset_type="equity",
            price_data={},
            preferences=NarrativePreferences(
                include_technical=True,
                include_fundamental=True,
            ),
        )

        quality_metrics = generator._validate_narrative_quality(narrative, context)

        # Should have low completeness score due to missing expected sections
        assert quality_metrics.completeness_score < 1.0

    def test_extract_risk_factors_with_various_conditions(self, mock_azure_client, sample_context):
        """Test risk factor extraction with different data conditions"""
        generator = NarrativeGenerator(azure_client=mock_azure_client)

        # High volatility
        sample_context.risk_data = {"volatility_30d": 45, "beta": 1.8}
        sample_context.fundamental_data = {"pe_ratio": 50}
        sample_context.technical_data = {"rsi": 75}

        risk_factors = generator._extract_risk_factors(sample_context, [])

        assert len(risk_factors) > 0
        assert any("volatility" in rf.lower() for rf in risk_factors)

    def test_fallback_extract_insights_various_scenarios(self, mock_azure_client):
        """Test fallback insights extraction with various data"""
        generator = NarrativeGenerator(azure_client=mock_azure_client)

        context = NarrativeContext(
            asset_symbol="TEST",
            asset_type="equity",
            price_data={"change_percent": 5.5},
            risk_data={"volatility_30d": 50},
            sentiment_data={"overall_score": 0.7},
        )

        insights = generator._fallback_extract_insights(context, [])

        assert len(insights) > 0
        assert len(insights) <= 5

    def test_generate_disclaimer_different_asset_types(self, mock_azure_client):
        """Test disclaimer generation for different asset types"""
        generator = NarrativeGenerator(azure_client=mock_azure_client)

        asset_types = ["equity", "crypto", "forex", "commodity", "etf", "unknown"]

        for asset_type in asset_types:
            context = NarrativeContext(
                asset_symbol="TEST",
                asset_type=asset_type,
                price_data={},
            )

            disclaimer = generator._generate_disclaimer(context)

            assert disclaimer is not None
            assert len(disclaimer) > 10

    @pytest.mark.asyncio
    async def test_generate_narrative_selective_sections(
        self, mock_azure_client, mock_llm_response, sample_context
    ):
        """Test narrative generation with selective sections"""
        mock_azure_client._make_request.return_value = mock_llm_response

        generator = NarrativeGenerator(azure_client=mock_azure_client)

        # Disable some sections
        sample_context.preferences.include_technical = False
        sample_context.preferences.include_sentiment = False

        narrative = await generator.generate_narrative(sample_context)

        # Should not have technical or sentiment sections
        assert narrative.get_section(NarrativeType.TECHNICAL) is None
        assert narrative.get_section(NarrativeType.SENTIMENT) is None

    def test_calculate_readability_edge_cases(self, mock_azure_client):
        """Test readability calculation with edge cases"""
        generator = NarrativeGenerator(azure_client=mock_azure_client)

        # Empty text
        score_empty = generator._calculate_readability("")
        assert score_empty == 60.0

        # Single word
        score_single = generator._calculate_readability("Hello")
        assert 0 <= score_single <= 100

    def test_count_syllables_edge_cases(self, mock_azure_client):
        """Test syllable counting edge cases"""
        generator = NarrativeGenerator(azure_client=mock_azure_client)

        # Silent e
        assert generator._count_syllables("time") >= 1
        assert generator._count_syllables("make") >= 1

        # Single letter
        assert generator._count_syllables("a") == 1
        assert generator._count_syllables("I") == 1
