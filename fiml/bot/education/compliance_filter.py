"""
Component 11: Educational Compliance Filter
Ensures all content is educational-only with no financial advice
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)


class ComplianceLevel(Enum):
    """Compliance check result levels"""
    SAFE = "safe"  # Educational content, no issues
    WARNING = "warning"  # Borderline, requires disclaimer
    BLOCKED = "blocked"  # Advice detected, must be blocked


@dataclass
class ComplianceFilterResult:
    """Result from filtering user questions"""
    is_allowed: bool
    message: str = ""
    alternative_suggestions: Optional[List[str]] = None

    def __post_init__(self) -> None:
        if self.alternative_suggestions is None:
            self.alternative_suggestions = []


class EducationalComplianceFilter:
    """
    Compliance filter for educational bot

    Features:
    - Detects financial advice language
    - Blocks investment recommendations
    - Ensures educational-only content
    - Regional compliance checks
    - Automatic disclaimers
    """

    # Prohibited advice patterns (high risk)
    ADVICE_PATTERNS = [
        r'\b(buy|sell|short|long)\s+(this|that|it|now)\b',
        r'\byou\s+should\s+(buy|sell|invest|trade)\b',
        r'\bi\s+recommend\s+(buying|selling|investing)\b',
        r'\bthis\s+is\s+a\s+(good|great|perfect)\s+(buy|opportunity)\b',
        r'\byou\s+will\s+(make|earn|profit)\b',
        r'\bguaranteed\s+(profit|returns?)\b',
        r'\bcan\'t\s+lose\b',
        r'\bsure\s+thing\b',
        r'\bhot\s+tip\b',
        r'\bget\s+rich\b',
    ]

    # Warning patterns (borderline, requires disclaimer)
    WARNING_PATTERNS = [
        r'\b(might|could|may)\s+(buy|sell|invest)\b',
        r'\b(might|could|may)\s+be\s+a\s+(good|great)\s+(investment|opportunity)\b',
        r'\b(consider|look\s+at|check\s+out)\s+(buying|selling)\b',
        r'\b(bullish|bearish)\s+on\b',
        r'\bpotential\s+(upside|downside)\b',
        r'\bgood\s+entry\s+point\b',
        r'\b(will|going\s+to)\s+(go\s+up|rise|increase|moon)\b',
    ]

    # Safe educational phrases (examples of good content)
    EDUCATIONAL_PHRASES = [
        "let's learn",
        "for example",
        "this explains",
        "historically",
        "the concept of",
        "in this lesson",
        "quiz question",
        "educational purposes",
    ]

    def __init__(self, region: str = "US"):
        """
        Initialize compliance filter

        Args:
            region: Region code for compliance rules
        """
        self.region = region
        self._advice_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.ADVICE_PATTERNS]
        self._warning_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.WARNING_PATTERNS]

        logger.info("EducationalComplianceFilter initialized", region=region)

    async def check_content(
        self,
        content: str,
        context: str = "general"
    ) -> Tuple[ComplianceLevel, str]:
        """
        Check content for compliance

        Args:
            content: Text to check
            context: Context (lesson, quiz, mentor, user_question)

        Returns:
            (compliance_level, message)
        """
        # Check for warning patterns BEFORE lowercasing
        for pattern in self._warning_regex:
            if pattern.search(content.lower()):
                logger.info("Warning pattern detected", pattern=pattern.pattern)
                return ComplianceLevel.WARNING, self.add_disclaimer(content, ComplianceLevel.WARNING)

        content = content.lower()

        # Check for prohibited advice
        for regex in self._advice_regex:
            match = regex.search(content)
            if match:
                matched_text = match.group(0)
                logger.warning(
                    "Advice pattern detected",
                    context=context,
                    pattern=matched_text
                )
                return (
                    ComplianceLevel.BLOCKED,
                    f"Content blocked: Contains advice language ('{matched_text}'). "
                    "Educational content only."
                )

        # Check for warning patterns
        for regex in self._warning_regex:
            match = regex.search(content)
            if match:
                matched_text = match.group(0)
                logger.info(
                    "Warning pattern detected",
                    context=context,
                    pattern=matched_text
                )
                return (
                    ComplianceLevel.WARNING,
                    f"Warning: Borderline language detected ('{matched_text}'). "
                    "Strong disclaimer required."
                )

        # Content is safe
        return (
            ComplianceLevel.SAFE,
            "Content is educational and compliant"
        )

    async def filter_user_question(self, question: str) -> ComplianceFilterResult:
        """
        Check if user question is seeking advice

        Args:
            question: User's question

        Returns:
            ComplianceFilterResult with is_allowed and alternative_suggestions
        """
        question_lower = question.lower().strip()

        # Direct advice seeking patterns
        advice_seeking = [
            r'\bshould\s+i\s+(buy|sell|invest|trade)\b',
            r'\bwhat\s+(stock|coin|crypto)\s+should\s+i\b',
            r'\bwhen\s+should\s+i\s+(buy|sell)\b',
            r'\bis\s+.+\s+a\s+good\s+(buy|investment)\b',
            r'\bwill\s+.+\s+go\s+up\b',
            r'\btell\s+me\s+what\s+to\s+(buy|sell)\b',
        ]

        for pattern in advice_seeking:
            if re.search(pattern, question_lower):
                return ComplianceFilterResult(
                    is_allowed=False,
                    message=(
                        "I can't provide investment advice! 🚫\n\n"
                        "Instead, I can help you:\n"
                        "• Learn how to analyze stocks yourself\n"
                        "• Understand key financial concepts\n"
                        "• Practice with real market data\n\n"
                        "Try asking one of these:"
                    ),
                    alternative_suggestions=[
                        "How do I analyze a stock?",
                        "What is P/E ratio?",
                        "How does technical analysis work?"
                    ]
                )

        # Question is educational
        return ComplianceFilterResult(is_allowed=True, message="")

    def add_disclaimer(
        self,
        content: str,
        level: ComplianceLevel = ComplianceLevel.WARNING
    ) -> str:
        """Add appropriate disclaimer to content"""

        if level == ComplianceLevel.SAFE:
            # Light disclaimer
            return f"{content}\n\n_Educational purposes only_"

        elif level == ComplianceLevel.WARNING:
            # Strong disclaimer
            return (
                f"{content}\n\n"
                "⚠️ **IMPORTANT DISCLAIMER**\n"
                "This is educational information only - NOT financial advice. "
                "Always do your own research and consult a licensed financial advisor "
                "before making investment decisions."
            )

        else:  # BLOCKED
            # Should not add disclaimer to blocked content
            return content

    async def check_and_filter(
        self,
        content: str,
        context: str = "general"
    ) -> Dict:
        """
        Check content and return filtered version

        Args:
            content: Content to check
            context: Context

        Returns:
            Dict with allowed, filtered_content, level, message
        """
        level, message = await self.check_content(content, context)

        if level == ComplianceLevel.BLOCKED:
            return {
                "allowed": False,
                "filtered_content": None,
                "level": level.value,
                "message": message
            }

        # Add appropriate disclaimer
        filtered = self.add_disclaimer(content, level)

        return {
            "allowed": True,
            "filtered_content": filtered,
            "level": level.value,
            "message": message
        }

    def get_regional_requirements(self) -> Dict:
        """Get compliance requirements for region"""

        requirements = {
            "US": {
                "requires_disclaimers": True,
                "prohibits_advice": True,
                "requires_registration": False,
                "notes": "Educational content allowed without registration"
            },
            "EU": {
                "requires_disclaimers": True,
                "prohibits_advice": True,
                "requires_registration": False,
                "notes": "GDPR compliance required"
            },
            "UK": {
                "requires_disclaimers": True,
                "prohibits_advice": True,
                "requires_registration": False,
                "notes": "FCA educational exemption"
            }
        }

        return requirements.get(self.region, requirements["US"])

    def escalate_concern(self, content: str, reason: str) -> None:
        """Log concerning content for review"""

        logger.warning(
            "Compliance concern escalated",
            region=self.region,
            reason=reason,
            content_preview=content[:100]
        )

        # In production, this would alert compliance team
