"""
Tests for EducationalComplianceFilter (Component 11)
"""

import pytest
from fiml.bot.education.compliance_filter import EducationalComplianceFilter, ComplianceLevel


class TestEducationalComplianceFilter:
    """Test compliance and safety filtering"""
    
    @pytest.fixture
    def compliance_filter(self):
        """Create a compliance filter"""
        return EducationalComplianceFilter()
    
    def test_safe_educational_content(self, compliance_filter):
        """Test that educational content is marked as safe"""
        content = "Stocks represent ownership in a company. The P/E ratio helps evaluate valuation."
        result = compliance_filter.check_content(content)
        
        assert result.level == ComplianceLevel.SAFE
        assert not result.requires_disclaimer
    
    def test_blocked_advice_patterns(self, compliance_filter):
        """Test detection of explicit advice patterns"""
        advice_phrases = [
            "You should buy Apple stock now",
            "I recommend selling Tesla",
            "This is a guaranteed profit",
            "You can't lose with this investment",
            "Hot tip: buy Bitcoin"
        ]
        
        for phrase in advice_phrases:
            result = compliance_filter.check_content(phrase)
            assert result.level == ComplianceLevel.BLOCKED
            assert len(result.flagged_phrases) > 0
    
    def test_warning_level_content(self, compliance_filter):
        """Test content that requires strong disclaimer"""
        warning_phrases = [
            "You might want to consider buying this stock",
            "This could be a good entry point",
            "I'm bullish on this company",
            "Many analysts think this will go up"
        ]
        
        for phrase in warning_phrases:
            result = compliance_filter.check_content(phrase)
            assert result.level == ComplianceLevel.WARNING
            assert result.requires_disclaimer
    
    def test_user_question_filtering(self, compliance_filter):
        """Test filtering of user questions seeking advice"""
        advice_seeking_questions = [
            "Should I buy Apple stock?",
            "Which stock is best to invest in?",
            "When should I sell my shares?",
            "Is now a good time to buy Tesla?"
        ]
        
        for question in advice_seeking_questions:
            result = compliance_filter.filter_user_question(question)
            assert not result.is_allowed
            assert len(result.alternative_suggestions) > 0
    
    def test_allowed_educational_questions(self, compliance_filter):
        """Test that educational questions are allowed"""
        educational_questions = [
            "What is a P/E ratio?",
            "How do I calculate dividend yield?",
            "What's the difference between stocks and bonds?",
            "How does inflation affect stock returns?"
        ]
        
        for question in educational_questions:
            result = compliance_filter.filter_user_question(question)
            assert result.is_allowed
    
    def test_disclaimer_injection(self, compliance_filter):
        """Test automatic disclaimer injection"""
        content = "High P/E ratios might indicate growth stocks."
        result = compliance_filter.check_content(content)
        
        if result.requires_disclaimer:
            disclaimer = compliance_filter.get_disclaimer(result.level)
            assert "not financial advice" in disclaimer.lower()
            assert "educational" in disclaimer.lower()
    
    def test_regional_compliance_us(self, compliance_filter):
        """Test US compliance requirements"""
        requirements = compliance_filter.get_regional_requirements("US")
        
        assert "no_advice" in requirements
        assert "disclaimers_required" in requirements
        assert requirements["regulatory_body"] == "SEC"
    
    def test_regional_compliance_eu(self, compliance_filter):
        """Test EU compliance requirements"""
        requirements = compliance_filter.get_regional_requirements("EU")
        
        assert "no_advice" in requirements
        assert "disclaimers_required" in requirements
        assert requirements["regulatory_body"] == "ESMA"
    
    def test_escalation_logging(self, compliance_filter):
        """Test logging of concerning content"""
        concerning_content = "Guaranteed 1000% returns! Buy now or miss out!"
        result = compliance_filter.check_content(concerning_content)
        
        assert result.level == ComplianceLevel.BLOCKED
        assert result.escalate
        
        # Check that escalation was logged
        logs = compliance_filter.get_escalation_log()
        assert len(logs) > 0
        assert any("Guaranteed" in log["content"] for log in logs)
    
    def test_multiple_violations(self, compliance_filter):
        """Test content with multiple compliance violations"""
        content = "You should definitely buy this stock. Guaranteed profit! Can't lose!"
        result = compliance_filter.check_content(content)
        
        assert result.level == ComplianceLevel.BLOCKED
        assert len(result.flagged_phrases) >= 3
    
    def test_case_insensitive_detection(self, compliance_filter):
        """Test that detection works regardless of case"""
        variations = [
            "YOU SHOULD BUY",
            "you should buy",
            "You Should Buy",
            "yOu ShOuLd BuY"
        ]
        
        for variation in variations:
            result = compliance_filter.check_content(variation)
            assert result.level == ComplianceLevel.BLOCKED
    
    def test_disclaimer_strength_levels(self, compliance_filter):
        """Test different disclaimer strengths for different compliance levels"""
        safe_disclaimer = compliance_filter.get_disclaimer(ComplianceLevel.SAFE)
        warning_disclaimer = compliance_filter.get_disclaimer(ComplianceLevel.WARNING)
        
        # Warning disclaimer should be stronger/longer
        assert len(warning_disclaimer) > len(safe_disclaimer)
        assert "strong" in warning_disclaimer.lower() or "not" in warning_disclaimer.lower()
    
    def test_suggestion_alternatives(self, compliance_filter):
        """Test alternative suggestions for blocked questions"""
        question = "Should I buy AAPL?"
        result = compliance_filter.filter_user_question(question)
        
        assert not result.is_allowed
        assert len(result.alternative_suggestions) > 0
        
        # Suggestions should be educational
        assert any("learn" in suggestion.lower() or "how" in suggestion.lower() 
                  for suggestion in result.alternative_suggestions)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
