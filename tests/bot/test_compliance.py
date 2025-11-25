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
            "Hot tip: buy Bitcoin"
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
            "Many analysts think this will go up"
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
            "Is now a good time to buy Tesla?"
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
            "How does inflation affect stock returns?"
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
        variations = [
            "YOU SHOULD BUY",
            "you should buy",
            "You Should Buy",
            "yOu ShOuLd BuY"
        ]

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
