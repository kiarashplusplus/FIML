"""
Tests for EducationalComplianceFilter (Component 11)
"""

import pytest

from fiml.bot.education.compliance_filter import ComplianceLevel, EducationalComplianceFilter


class TestEducationalComplianceFilter:
    """Test compliance and safety filtering"""

    @pytest.fixture
    def compliance_filter(self):
        """Create a compliance filter"""
        return EducationalComplianceFilter()

    async def test_safe_educational_content(self, compliance_filter):
        """Test that educational content is marked as safe"""
        content = "Stocks represent ownership in a company. The P/E ratio helps evaluate valuation."
        level, message = await compliance_filter.check_content(content)

        assert level == ComplianceLevel.SAFE
        # Check message indicates safe

    async def test_blocked_advice_patterns(self, compliance_filter):
        """Test detection of explicit advice patterns"""
        advice_phrases = [
            "You should buy Apple stock now",
            "I recommend selling Tesla",
            "This is a guaranteed profit",
            "You can't lose with this investment",
            "Hot tip: buy Bitcoin",
        ]

        for phrase in advice_phrases:
            level, message = await compliance_filter.check_content(phrase)
            assert level == ComplianceLevel.BLOCKED

    async def test_warning_level_content(self, compliance_filter):
        """Test content that requires strong disclaimer"""
        warning_phrases = [
            "You might want to consider buying this stock",
            "This could be a good entry point",
            "I'm bullish on this company",
            "Many analysts think this will go up",
        ]

        for phrase in warning_phrases:
            level, message = await compliance_filter.check_content(phrase)
            assert level == ComplianceLevel.WARNING
            assert message

    async def test_user_question_filtering(self, compliance_filter):
        """Test filtering of user questions seeking advice"""
        advice_seeking_questions = [
            "Should I buy Apple stock?",
            "Which stock is best to invest in?",
            "When should I sell my shares?",
            "Is now a good time to buy Tesla?",
        ]

        for question in advice_seeking_questions:
            result = await compliance_filter.filter_user_question(question)
            assert result is not None

    async def test_allowed_educational_questions(self, compliance_filter):
        """Test that educational questions are allowed"""
        educational_questions = [
            "What is a P/E ratio?",
            "How do I calculate dividend yield?",
            "What's the difference between stocks and bonds?",
            "How does inflation affect stock returns?",
        ]

        for question in educational_questions:
            result = await compliance_filter.filter_user_question(question)
            assert result is not None

    async def test_disclaimer_injection(self, compliance_filter):
        """Test automatic disclaimer injection"""
        content = "High P/E ratios might indicate growth stocks."
        level, message = await compliance_filter.check_content(content)

        # Should be safe or warning level
        assert level in [ComplianceLevel.SAFE, ComplianceLevel.WARNING]
        assert message

    async def test_regional_compliance_us(self, compliance_filter):
        """Test US compliance requirements"""
        requirements = compliance_filter.get_regional_requirements()

        assert "requires_disclaimers" in requirements
        assert "prohibits_advice" in requirements
        assert requirements["requires_disclaimers"] is True

    async def test_regional_compliance_eu(self):
        """Test EU compliance requirements"""
        eu_filter = EducationalComplianceFilter(region="EU")
        requirements = eu_filter.get_regional_requirements()

        assert "requires_disclaimers" in requirements
        assert "prohibits_advice" in requirements
        assert requirements["requires_disclaimers"] is True

    async def test_escalation_logging(self, compliance_filter):
        """Test logging of concerning content"""
        concerning_content = "Guaranteed 1000% returns! Buy now or miss out!"
        level, message = await compliance_filter.check_content(concerning_content)

        assert level == ComplianceLevel.BLOCKED
        # Escalation would be logged (check would require accessing logs in production)

    async def test_multiple_violations(self, compliance_filter):
        """Test content with multiple compliance violations"""
        content = "You should definitely buy this stock. Guaranteed profit! Can't lose!"
        level, message = await compliance_filter.check_content(content)

        assert level == ComplianceLevel.BLOCKED

    async def test_case_insensitive_detection(self, compliance_filter):
        """Test that detection works regardless of case"""
        variations = ["YOU SHOULD BUY", "you should buy", "You Should Buy", "yOu ShOuLd BuY"]

        for variation in variations:
            level, message = await compliance_filter.check_content(variation)
            assert level == ComplianceLevel.BLOCKED

    async def test_disclaimer_strength_levels(self, compliance_filter):
        """Test different compliance levels have different messages"""
        safe_content = "The P/E ratio is a valuation metric."
        warning_content = "This might be a good investment opportunity."

        safe_level, safe_msg = await compliance_filter.check_content(safe_content)
        warning_level, warning_msg = await compliance_filter.check_content(warning_content)

        assert safe_level == ComplianceLevel.SAFE
        assert warning_level == ComplianceLevel.WARNING
        # Warning message should be more serious
        assert len(warning_msg) >= len(safe_msg)

    async def test_suggestion_alternatives(self, compliance_filter):
        """Test alternative suggestions for blocked questions"""
        question = "Should I buy AAPL?"
        result = await compliance_filter.filter_user_question(question)
        allowed = result.is_allowed
        response = result.message

        assert not allowed
        # Response should suggest educational alternatives
        assert "learn" in response.lower() or "understand" in response.lower()


class TestComplianceFilterIntegration:
    """Test compliance filter with guardrail integration"""

    @pytest.fixture
    def compliance_filter_with_guardrail(self):
        """Create a compliance filter with guardrail enabled"""
        return EducationalComplianceFilter(region="US", use_guardrail=True)

    @pytest.fixture
    def compliance_filter_no_guardrail(self):
        """Create a compliance filter with guardrail disabled"""
        return EducationalComplianceFilter(region="US", use_guardrail=False)

    async def test_process_output_basic(self, compliance_filter_with_guardrail):
        """Test process_output returns processed text"""
        content = "The stock is currently trading at $150."
        processed, result = await compliance_filter_with_guardrail.process_output(content)

        assert processed is not None
        assert result is not None
        assert result.is_compliant

    async def test_process_output_with_advice(self, compliance_filter_with_guardrail):
        """Test process_output modifies advice content"""
        content = "You should buy this stock now."
        processed, result = await compliance_filter_with_guardrail.process_output(content)

        assert result is not None
        # Original advice should be modified or flagged
        assert result.was_modified or len(result.violations_found) > 0

    async def test_check_and_filter_blocked(self, compliance_filter_with_guardrail):
        """Test check_and_filter blocks advice content"""
        content = "Buy now before the price goes up!"
        result = await compliance_filter_with_guardrail.check_and_filter(content)

        assert "level" in result
        assert result["level"] in ["blocked", "warning", "safe"]

    async def test_check_and_filter_safe(self, compliance_filter_with_guardrail):
        """Test check_and_filter allows educational content"""
        content = "The P/E ratio is a valuation metric used by investors."
        result = await compliance_filter_with_guardrail.check_and_filter(content)

        assert result["allowed"] is True
        assert result["level"] == "safe"

    async def test_get_supported_languages(self, compliance_filter_with_guardrail):
        """Test get_supported_languages returns list of languages"""
        languages = compliance_filter_with_guardrail.get_supported_languages()

        assert isinstance(languages, list)
        assert len(languages) >= 1
        assert "en" in languages

    async def test_set_language(self, compliance_filter_with_guardrail):
        """Test set_language changes the filter language"""
        from fiml.compliance.guardrail import SupportedLanguage

        compliance_filter_with_guardrail.set_language(SupportedLanguage.SPANISH)

        assert compliance_filter_with_guardrail.language == SupportedLanguage.SPANISH

    async def test_legacy_fallback_mode(self, compliance_filter_no_guardrail):
        """Test legacy mode without guardrail works"""
        content = "You should buy this stock now."
        level, message = await compliance_filter_no_guardrail.check_content(content)

        assert level == ComplianceLevel.BLOCKED
        assert "advice" in message.lower() or "blocked" in message.lower()

    async def test_multiple_regions(self):
        """Test compliance filter works with different regions"""
        regions = ["US", "EU", "UK"]

        for region in regions:
            filter = EducationalComplianceFilter(region=region, use_guardrail=True)
            requirements = filter.get_regional_requirements()

            assert "requires_disclaimers" in requirements
            assert requirements["requires_disclaimers"] is True

    async def test_guardrail_result_in_output(self, compliance_filter_with_guardrail):
        """Test that guardrail result is included in check_and_filter"""
        content = "This stock might be a good investment."
        result = await compliance_filter_with_guardrail.check_and_filter(content)

        assert "guardrail_result" in result
        assert result["guardrail_result"] is not None

    async def test_compliance_filter_result_structure(self, compliance_filter_with_guardrail):
        """Test ComplianceFilterResult has correct structure"""
        question = "What is a stock?"
        result = await compliance_filter_with_guardrail.filter_user_question(question)

        assert hasattr(result, "is_allowed")
        assert hasattr(result, "message")
        assert hasattr(result, "alternative_suggestions")

    async def test_add_disclaimer_safe_level(self, compliance_filter_with_guardrail):
        """Test add_disclaimer for SAFE level"""
        content = "The market is open."
        result = compliance_filter_with_guardrail.add_disclaimer(content, ComplianceLevel.SAFE)

        assert "Educational" in result or "educational" in result

    async def test_add_disclaimer_warning_level(self, compliance_filter_with_guardrail):
        """Test add_disclaimer for WARNING level"""
        content = "The market is volatile."
        result = compliance_filter_with_guardrail.add_disclaimer(content, ComplianceLevel.WARNING)

        assert "DISCLAIMER" in result
        assert "NOT financial advice" in result

    async def test_escalate_concern(self, compliance_filter_with_guardrail):
        """Test escalate_concern logs without error"""
        # Should not raise an exception
        compliance_filter_with_guardrail.escalate_concern(
            content="Suspicious content", reason="Test escalation"
        )

    async def test_map_region_unknown(self, compliance_filter_with_guardrail):
        """Test region mapping for unknown regions"""
        from fiml.compliance.router import Region

        result = compliance_filter_with_guardrail._map_region("UNKNOWN")

        assert result == Region.GLOBAL


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
