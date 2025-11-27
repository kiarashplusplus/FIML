"""
Component 11: Educational Compliance Filter
Ensures all content is educational-only with no financial advice.
Integrates with FIML's ComplianceGuardrail for comprehensive compliance checking.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

import structlog

from fiml.compliance.disclaimers import AssetClass
from fiml.compliance.guardrail import (
    ComplianceGuardrail,
    GuardrailAction,
    GuardrailResult,
    SupportedLanguage,
)
from fiml.compliance.router import Region

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
    guardrail_result: Optional[GuardrailResult] = None

    def __post_init__(self) -> None:
        if self.alternative_suggestions is None:
            self.alternative_suggestions = []


class EducationalComplianceFilter:
    """
    Compliance filter for educational bot integrated with FIML ComplianceGuardrail

    Features:
    - Detects financial advice language using ComplianceGuardrail
    - Blocks investment recommendations
    - Ensures educational-only content
    - Regional compliance checks
    - Automatic disclaimers
    - Multilingual support (9 languages)
    """

    # Prohibited advice patterns (high risk) - legacy patterns for quick checks
    ADVICE_PATTERNS = [
        r"\b(buy|sell|short|long)\s+(this|that|it|now)\b",
        r"\byou\s+should\s+(buy|sell|invest|trade)\b",
        r"\bi\s+recommend\s+(buying|selling|investing)\b",
        r"\bthis\s+is\s+a\s+(good|great|perfect)\s+(buy|opportunity)\b",
        r"\byou\s+will\s+(make|earn|profit)\b",
        r"\bguaranteed\s+(profit|returns?)\b",
        r"\bcan\'t\s+lose\b",
        r"\bsure\s+thing\b",
        r"\bhot\s+tip\b",
        r"\bget\s+rich\b",
    ]

    # Warning patterns (borderline, requires disclaimer)
    WARNING_PATTERNS = [
        r"\b(might|could|may)\s+(buy|sell|invest)\b",
        r"\b(might|could|may)\s+be\s+a\s+(good|great)\s+(investment|opportunity)\b",
        r"\b(consider|look\s+at|check\s+out)\s+(buying|selling)\b",
        r"\b(bullish|bearish)\s+on\b",
        r"\bpotential\s+(upside|downside)\b",
        r"\bgood\s+entry\s+point\b",
        r"\b(will|going\s+to)\s+(go\s+up|rise|increase|moon)\b",
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

    def __init__(
        self,
        region: str = "US",
        language: SupportedLanguage = SupportedLanguage.ENGLISH,
        use_guardrail: bool = True,
    ):
        """
        Initialize compliance filter with ComplianceGuardrail integration

        Args:
            region: Region code for compliance rules (US, EU, UK, etc.)
            language: Language for compliance checking
            use_guardrail: Whether to use the ComplianceGuardrail (default: True)
        """
        self.region = region
        self.language = language
        self.use_guardrail = use_guardrail

        # Initialize the ComplianceGuardrail
        self._guardrail = ComplianceGuardrail(
            strict_mode=True,  # Block content with too many violations
            auto_add_disclaimer=True,
        )

        # Legacy regex patterns for quick checks
        self._advice_regex = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.ADVICE_PATTERNS
        ]
        self._warning_regex = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.WARNING_PATTERNS
        ]

        logger.info(
            "EducationalComplianceFilter initialized with ComplianceGuardrail",
            region=region,
            language=language.value,
            use_guardrail=use_guardrail,
        )

    def _map_region(self, region: str) -> Region:
        """Map string region to Region enum"""
        region_map = {
            "US": Region.US,
            "EU": Region.EU,
            "UK": Region.UK,
            "JP": Region.JP,
        }
        return region_map.get(region, Region.GLOBAL)

    async def check_content(
        self, content: str, context: str = "general"
    ) -> Tuple[ComplianceLevel, str]:
        """
        Check content for compliance using ComplianceGuardrail

        Args:
            content: Text to check
            context: Context (lesson, quiz, mentor, user_question)

        Returns:
            (compliance_level, message)
        """
        # ALWAYS check legacy advice patterns first for BLOCKED status
        # This ensures backwards compatibility with existing tests
        content_lower = content.lower()
        for regex in self._advice_regex:
            match = regex.search(content_lower)
            if match:
                matched_text = match.group(0)
                logger.warning(
                    "Advice pattern detected - BLOCKED",
                    context=context,
                    pattern=matched_text,
                )
                return (
                    ComplianceLevel.BLOCKED,
                    f"Content blocked: Contains advice language ('{matched_text}'). "
                    "Educational content only.",
                )

        if self.use_guardrail:
            # Use the comprehensive ComplianceGuardrail for additional checks
            result = self._guardrail.process(
                content,
                asset_class=AssetClass.EQUITY,
                region=self._map_region(self.region),
                language=self.language,
            )

            if result.action == GuardrailAction.BLOCKED:
                logger.warning(
                    "Content blocked by ComplianceGuardrail",
                    context=context,
                    violations=len(result.violations_found),
                )
                return (
                    ComplianceLevel.BLOCKED,
                    f"Content blocked: Contains advice language. "
                    f"Violations: {len(result.violations_found)}. Educational content only.",
                )

            # Check for warning patterns
            for regex in self._warning_regex:
                match = regex.search(content_lower)
                if match:
                    matched_text = match.group(0)
                    logger.info(
                        "Warning pattern detected",
                        context=context,
                        pattern=matched_text,
                    )
                    return (
                        ComplianceLevel.WARNING,
                        self.add_disclaimer(content, ComplianceLevel.WARNING),
                    )

            if result.was_modified or result.violations_found:
                logger.info(
                    "Content modified by ComplianceGuardrail",
                    context=context,
                    modifications=len(result.modifications),
                )
                return (
                    ComplianceLevel.WARNING,
                    result.processed_text,
                )

            return (ComplianceLevel.SAFE, "Content is educational and compliant")

        # Legacy pattern matching (fallback)
        return await self._check_content_legacy(content, context)

    async def _check_content_legacy(
        self, content: str, context: str
    ) -> Tuple[ComplianceLevel, str]:
        """Legacy pattern-based content checking"""
        # Check for warning patterns BEFORE lowercasing
        for pattern in self._warning_regex:
            if pattern.search(content.lower()):
                logger.info("Warning pattern detected", pattern=pattern.pattern)
                return ComplianceLevel.WARNING, self.add_disclaimer(
                    content, ComplianceLevel.WARNING
                )

        content_lower = content.lower()

        # Check for prohibited advice
        for regex in self._advice_regex:
            match = regex.search(content_lower)
            if match:
                matched_text = match.group(0)
                logger.warning("Advice pattern detected", context=context, pattern=matched_text)
                return (
                    ComplianceLevel.BLOCKED,
                    f"Content blocked: Contains advice language ('{matched_text}'). "
                    "Educational content only.",
                )

        # Check for warning patterns
        for regex in self._warning_regex:
            match = regex.search(content_lower)
            if match:
                matched_text = match.group(0)
                logger.info("Warning pattern detected", context=context, pattern=matched_text)
                return (
                    ComplianceLevel.WARNING,
                    f"Warning: Borderline language detected ('{matched_text}'). "
                    "Strong disclaimer required.",
                )

        return (ComplianceLevel.SAFE, "Content is educational and compliant")

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
            r"\bshould\s+i\s+(buy|sell|invest|trade)\b",
            r"\bwhat\s+(stock|coin|crypto)\s+should\s+i\b",
            r"\bwhen\s+should\s+i\s+(buy|sell)\b",
            r"\bis\s+.+\s+a\s+good\s+(buy|investment)\b",
            r"\bwill\s+.+\s+go\s+up\b",
            r"\btell\s+me\s+what\s+to\s+(buy|sell)\b",
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
                        "How does technical analysis work?",
                    ],
                )

        # Question is educational
        return ComplianceFilterResult(is_allowed=True, message="")

    def add_disclaimer(self, content: str, level: ComplianceLevel = ComplianceLevel.WARNING) -> str:
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

    async def process_output(
        self,
        content: str,
        context: str = "general",
        asset_class: AssetClass = AssetClass.EQUITY,
    ) -> Tuple[str, GuardrailResult]:
        """
        Process output through the ComplianceGuardrail

        This is the primary method for ensuring all bot output is compliant.

        Args:
            content: Content to process
            context: Context for logging
            asset_class: Type of asset for disclaimer customization

        Returns:
            Tuple of (processed_content, guardrail_result)
        """
        result = self._guardrail.process(
            content,
            asset_class=asset_class,
            region=self._map_region(self.region),
            language=self.language,
        )

        logger.info(
            "Output processed through ComplianceGuardrail",
            context=context,
            action=result.action.value,
            modifications=len(result.modifications),
            violations=len(result.violations_found),
            disclaimer_added=result.disclaimer_added,
        )

        return result.processed_text, result

    async def check_and_filter(self, content: str, context: str = "general") -> Dict:
        """
        Check content and return filtered version using ComplianceGuardrail

        Args:
            content: Content to check
            context: Context

        Returns:
            Dict with allowed, filtered_content, level, message
        """
        processed_text, result = await self.process_output(content, context)

        if result.action == GuardrailAction.BLOCKED:
            return {
                "allowed": False,
                "filtered_content": None,
                "level": ComplianceLevel.BLOCKED.value,
                "message": f"Content blocked: {len(result.violations_found)} violations found",
                "guardrail_result": result,
            }

        level = ComplianceLevel.WARNING if result.was_modified else ComplianceLevel.SAFE

        return {
            "allowed": True,
            "filtered_content": processed_text,
            "level": level.value,
            "message": "Content processed and compliant",
            "guardrail_result": result,
        }

    def get_regional_requirements(self) -> Dict:
        """Get compliance requirements for region"""

        requirements = {
            "US": {
                "requires_disclaimers": True,
                "prohibits_advice": True,
                "requires_registration": False,
                "notes": "Educational content allowed without registration",
            },
            "EU": {
                "requires_disclaimers": True,
                "prohibits_advice": True,
                "requires_registration": False,
                "notes": "GDPR compliance required",
            },
            "UK": {
                "requires_disclaimers": True,
                "prohibits_advice": True,
                "requires_registration": False,
                "notes": "FCA educational exemption",
            },
        }

        return requirements.get(self.region, requirements["US"])

    def escalate_concern(self, content: str, reason: str) -> None:
        """Log concerning content for review"""

        logger.warning(
            "Compliance concern escalated",
            region=self.region,
            reason=reason,
            content_preview=content[:100],
        )

        # In production, this would alert compliance team

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages from the guardrail"""
        return self._guardrail.get_supported_languages()

    def set_language(self, language: SupportedLanguage) -> None:
        """
        Set the language for compliance checking

        Args:
            language: SupportedLanguage enum value
        """
        self.language = language
        logger.info("Compliance filter language updated", language=language.value)
