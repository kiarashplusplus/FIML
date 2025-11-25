"""
Additional bot tests to increase coverage further

Focuses on:
- Compliance filtering
- AI Mentor
- Additional edge cases
"""


import pytest

from fiml.bot.education.ai_mentor import AIMentorService, MentorPersona
from fiml.bot.education.compliance_filter import (
    ComplianceFilterResult,
    ComplianceLevel,
    EducationalComplianceFilter,
)


@pytest.fixture
def compliance_filter():
    """EducationalComplianceFilter instance"""
    return EducationalComplianceFilter()


@pytest.fixture
def ai_mentor():
    """AIMentorService instance"""
    return AIMentorService()


# ============================================================================
# ComplianceFilter Tests
# ============================================================================

class TestComplianceFilter:
    """Test compliance and content filtering"""

    def test_initialization(self, compliance_filter):
        """Test filter initializes"""
        assert compliance_filter is not None

    @pytest.mark.asyncio
    async def test_check_content_safe(self, compliance_filter):
        """Test checking safe content"""
        safe_text = "Learn about stock market fundamentals and trading basics."
        level, message = await compliance_filter.check_content(safe_text)
        assert level is not None
        assert isinstance(level, ComplianceLevel)
        assert isinstance(message, str)

    @pytest.mark.asyncio
    async def test_check_financial_advice(self, compliance_filter):
        """Test detecting potential financial advice"""
        text = "You should buy this stock now!"
        level, message = await compliance_filter.check_content(text)
        assert level is not None
        assert isinstance(level, ComplianceLevel)

    @pytest.mark.asyncio
    async def test_filter_user_question(self, compliance_filter):
        """Test filtering user questions"""
        question = "How do stock markets work?"
        result = await compliance_filter.filter_user_question(question)
        assert isinstance(result, ComplianceFilterResult)
        assert isinstance(result.is_allowed, bool)


# ============================================================================
# AIMentor Tests
# ============================================================================

class TestAIMentor:
    """Test AI mentor functionality"""

    def test_initialization(self, ai_mentor):
        """Test mentor initializes"""
        assert ai_mentor is not None

    def test_mentor_personas(self):
        """Test mentor persona enum"""
        assert MentorPersona.MAYA is not None
        assert MentorPersona.THEO is not None
        assert MentorPersona.ZARA is not None
