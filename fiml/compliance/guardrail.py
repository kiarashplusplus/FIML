"""
Compliance Guardrail Layer

A final processing layer that:
- Scans outputs for advice-like language
- Removes/replaces advice-like language
- Blocks prescriptive verbs
- Ensures the tone is descriptive only
- Adds disclaimers automatically
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from fiml.compliance.disclaimers import AssetClass, DisclaimerGenerator
from fiml.compliance.router import Region
from fiml.core.logging import get_logger

logger = get_logger(__name__)


class GuardrailAction(str, Enum):
    """Actions that can be taken by the guardrail"""

    PASSED = "passed"  # Content is compliant
    MODIFIED = "modified"  # Content was modified to be compliant
    BLOCKED = "blocked"  # Content was blocked due to severe violations


@dataclass
class GuardrailResult:
    """Result of guardrail processing"""

    action: GuardrailAction
    original_text: str
    processed_text: str
    modifications: List[str] = field(default_factory=list)
    violations_found: List[str] = field(default_factory=list)
    disclaimer_added: bool = False
    confidence: float = 1.0

    @property
    def was_modified(self) -> bool:
        """Check if the text was modified"""
        return self.action == GuardrailAction.MODIFIED

    @property
    def is_compliant(self) -> bool:
        """Check if the result is compliant (passed or modified)"""
        return self.action in (GuardrailAction.PASSED, GuardrailAction.MODIFIED)


class ComplianceGuardrail:
    """
    Compliance Guardrail Layer for financial outputs

    Ensures all outputs are descriptive only and do not contain
    investment advice, recommendations, or prescriptive language.

    Example usage:
        >>> guardrail = ComplianceGuardrail()
        >>> result = guardrail.process("You should buy AAPL stock now!")
        >>> print(result.processed_text)
        "AAPL stock is currently available for trading."
        >>> print(result.was_modified)
        True
    """

    # Prescriptive verbs that indicate advice (with word boundaries)
    PRESCRIPTIVE_VERBS: List[str] = [
        r"\bshould\b",
        r"\bmust\b",
        r"\bought to\b",
        r"\bneed to\b",
        r"\bhave to\b",
        r"\bbetter to\b",
        r"\badvise\b",
        r"\brecommend\b",
        r"\bsuggest\b",
        r"\burge\b",
        r"\bencourage\b",
    ]

    # Advice-like language patterns (more specific than just verbs)
    ADVICE_PATTERNS: List[Tuple[str, str]] = [
        # Direct advice patterns
        (r"\byou should (buy|sell|invest|hold|trade)\b", "consider reviewing"),
        (
            r"\bi (recommend|suggest|advise) (that you |you )?(buy|sell|invest|hold)\b",
            "data indicates",
        ),
        (
            r"\b(buy|sell|invest in|trade) (now|immediately|today|asap)\b",
            "is currently available for trading",
        ),
        (
            r"\bthis is a (good|great|excellent|perfect) (time|opportunity) to (buy|sell|invest)\b",
            "current market conditions exist",
        ),
        (r"\bdon'?t (buy|sell|invest)\b", "current conditions may warrant review"),
        (r"\bavoid (buying|selling|investing)\b", "current conditions may warrant review"),
        # Strong buy/sell recommendations
        (r"\bstrong (buy|sell)\b", "notable activity"),
        (r"\boverweight\b", "increased allocation noted"),
        (r"\bunderweight\b", "decreased allocation noted"),
        # Prediction patterns
        (
            r"\bwill (definitely|certainly|surely|absolutely) (go|rise|fall|increase|decrease)\b",
            "has shown movement",
        ),
        (r"\bguaranteed to\b", "has historically shown"),
        (r"\bsure to\b", "has historically shown"),
        (r"\bwill reach \$\d+", "is at current levels"),
        (r"\bprice target\b", "current price level"),
        # Action imperative patterns
        (r"\b(buy|sell|get|grab|dump|hold) (it|this|these|the stock)\b", "it is currently trading"),
        (r"\bget in (now|before|while)\b", "current trading activity observed"),
        (r"\bget out (now|before|while)\b", "current trading activity observed"),
        (r"\bjump in\b", "current trading activity observed"),
        (r"\bpull out\b", "current trading activity observed"),
    ]

    # Patterns that indicate opinion presented as fact
    OPINION_AS_FACT_PATTERNS: List[Tuple[str, str]] = [
        (
            r"\bthis (stock|asset|investment) is (undervalued|overvalued)\b",
            "this asset has current metrics",
        ),
        (r"\b(definitely|certainly|obviously|clearly) a (buy|sell|hold)\b", "currently trading"),
        (r"\bno-brainer\b", "current data available"),
        (r"\beasy money\b", "trading opportunity present"),
        (r"\bcannot lose\b", "risk is inherent in trading"),
        (r"\brisk-free\b", "with associated risks"),
    ]

    # Future certainty language to convert to descriptive
    CERTAINTY_PATTERNS: List[Tuple[str, str]] = [
        (r"\bwill (increase|rise|go up|climb|surge)\b", "has shown upward movement"),
        (r"\bwill (decrease|fall|drop|decline|plunge)\b", "has shown downward movement"),
        (r"\bgoing to (increase|rise|go up)\b", "has recently moved"),
        (r"\bgoing to (decrease|fall|drop)\b", "has recently moved"),
        (r"\bexpect(?:ed|s)? to (reach|hit|exceed)\b", "has historically reached"),
        (r"\blikely to (increase|rise|go up)\b", "has shown positive trends"),
        (r"\blikely to (decrease|fall|drop)\b", "has shown negative trends"),
        (r"\bpredicted to\b", "has shown historical patterns of"),
        (r"\bforecast(?:ed)? to\b", "has shown historical patterns of"),
    ]

    # Required disclaimer phrases that must be present
    REQUIRED_DISCLAIMER_PHRASES: List[str] = [
        "not financial advice",
        "not investment advice",
        "informational purposes only",
        "educational purposes only",
        "data analysis only",
        "consult a financial advisor",
        "consult a qualified professional",
        "past performance",
        # Multilingual support
        "no es asesoramiento financiero",
        "n'est pas un conseil financier",
    ]

    def __init__(
        self,
        disclaimer_generator: Optional[DisclaimerGenerator] = None,
        strict_mode: bool = False,
        auto_add_disclaimer: bool = True,
    ):
        """
        Initialize the Compliance Guardrail

        Args:
            disclaimer_generator: Generator for disclaimers (creates new if None)
            strict_mode: If True, blocks content with severe violations instead of modifying
            auto_add_disclaimer: If True, automatically adds disclaimers when missing
        """
        self.disclaimer_generator = disclaimer_generator or DisclaimerGenerator()
        self.strict_mode = strict_mode
        self.auto_add_disclaimer = auto_add_disclaimer

        # Compile regex patterns for efficiency
        self._compiled_prescriptive = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.PRESCRIPTIVE_VERBS
        ]
        self._compiled_advice = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in self.ADVICE_PATTERNS
        ]
        self._compiled_opinion = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in self.OPINION_AS_FACT_PATTERNS
        ]
        self._compiled_certainty = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in self.CERTAINTY_PATTERNS
        ]

        logger.info(
            "Compliance guardrail initialized",
            strict_mode=strict_mode,
            auto_add_disclaimer=auto_add_disclaimer,
        )

    def process(
        self,
        text: str,
        asset_class: AssetClass = AssetClass.EQUITY,
        region: Region = Region.US,
    ) -> GuardrailResult:
        """
        Process text through the compliance guardrail

        Args:
            text: Input text to process
            asset_class: Type of asset for disclaimer customization
            region: User's region for compliance requirements

        Returns:
            GuardrailResult with processed text and modification details
        """
        if not text or not text.strip():
            return GuardrailResult(
                action=GuardrailAction.PASSED,
                original_text=text,
                processed_text=text,
            )

        violations: List[str] = []
        modifications: List[str] = []
        processed_text = text

        # Step 1: Scan for violations
        violations.extend(self._scan_for_prescriptive_verbs(text))
        violations.extend(self._scan_for_advice_patterns(text))
        violations.extend(self._scan_for_opinion_patterns(text))
        violations.extend(self._scan_for_certainty_patterns(text))

        # Step 2: If violations found in strict mode, block the content
        if self.strict_mode and len(violations) > 5:
            logger.warning(
                "Content blocked due to excessive violations",
                violation_count=len(violations),
            )
            return GuardrailResult(
                action=GuardrailAction.BLOCKED,
                original_text=text,
                processed_text="",
                violations_found=violations,
                confidence=0.0,
            )

        # Step 3: Remove/replace advice-like language
        processed_text, advice_mods = self._remove_advice_language(processed_text)
        modifications.extend(advice_mods)

        # Step 4: Remove/replace opinion as fact patterns
        processed_text, opinion_mods = self._remove_opinion_patterns(processed_text)
        modifications.extend(opinion_mods)

        # Step 5: Convert certainty language to descriptive
        processed_text, certainty_mods = self._convert_certainty_language(processed_text)
        modifications.extend(certainty_mods)

        # Step 6: Ensure descriptive tone
        processed_text, tone_mods = self._ensure_descriptive_tone(processed_text)
        modifications.extend(tone_mods)

        # Step 7: Check and add disclaimer if needed
        disclaimer_added = False
        if self.auto_add_disclaimer and not self._has_disclaimer(processed_text):
            disclaimer = self.disclaimer_generator.generate(
                asset_class=asset_class,
                region=region,
                include_general=True,
            )
            processed_text = self._add_disclaimer(processed_text, disclaimer)
            disclaimer_added = True
            modifications.append("Added compliance disclaimer")

        # Determine action
        if not modifications and not violations:
            action = GuardrailAction.PASSED
        else:
            action = GuardrailAction.MODIFIED

        # Calculate confidence based on modifications
        confidence = self._calculate_confidence(len(violations), len(modifications))

        logger.info(
            "Guardrail processing complete",
            action=action.value,
            violations=len(violations),
            modifications=len(modifications),
            disclaimer_added=disclaimer_added,
        )

        return GuardrailResult(
            action=action,
            original_text=text,
            processed_text=processed_text,
            modifications=modifications,
            violations_found=violations,
            disclaimer_added=disclaimer_added,
            confidence=confidence,
        )

    def scan_only(self, text: str) -> List[str]:
        """
        Scan text for violations without modifying it

        Args:
            text: Input text to scan

        Returns:
            List of violations found
        """
        violations = []
        violations.extend(self._scan_for_prescriptive_verbs(text))
        violations.extend(self._scan_for_advice_patterns(text))
        violations.extend(self._scan_for_opinion_patterns(text))
        violations.extend(self._scan_for_certainty_patterns(text))
        return violations

    def is_compliant(self, text: str) -> bool:
        """
        Check if text is already compliant

        Args:
            text: Input text to check

        Returns:
            True if text is compliant, False otherwise
        """
        violations = self.scan_only(text)
        has_disclaimer = self._has_disclaimer(text)
        return len(violations) == 0 and (has_disclaimer or not self.auto_add_disclaimer)

    def add_disclaimer(
        self,
        text: str,
        asset_class: AssetClass = AssetClass.EQUITY,
        region: Region = Region.US,
    ) -> str:
        """
        Add a disclaimer to text if not already present

        Args:
            text: Input text
            asset_class: Type of asset for disclaimer customization
            region: User's region for compliance requirements

        Returns:
            Text with disclaimer added
        """
        if self._has_disclaimer(text):
            return text

        disclaimer = self.disclaimer_generator.generate(
            asset_class=asset_class,
            region=region,
            include_general=True,
        )
        return self._add_disclaimer(text, disclaimer)

    def _scan_for_prescriptive_verbs(self, text: str) -> List[str]:
        """Scan for prescriptive verbs in text"""
        violations = []
        for pattern in self._compiled_prescriptive:
            matches = pattern.findall(text)
            if matches:
                violations.append(f"Prescriptive verb found: {pattern.pattern}")
        return violations

    def _scan_for_advice_patterns(self, text: str) -> List[str]:
        """Scan for advice patterns in text"""
        violations = []
        for pattern, _ in self._compiled_advice:
            if pattern.search(text):
                violations.append(f"Advice pattern found: {pattern.pattern}")
        return violations

    def _scan_for_opinion_patterns(self, text: str) -> List[str]:
        """Scan for opinion-as-fact patterns in text"""
        violations = []
        for pattern, _ in self._compiled_opinion:
            if pattern.search(text):
                violations.append(f"Opinion pattern found: {pattern.pattern}")
        return violations

    def _scan_for_certainty_patterns(self, text: str) -> List[str]:
        """Scan for certainty patterns in text"""
        violations = []
        for pattern, _ in self._compiled_certainty:
            if pattern.search(text):
                violations.append(f"Certainty pattern found: {pattern.pattern}")
        return violations

    def _remove_advice_language(self, text: str) -> Tuple[str, List[str]]:
        """Remove or replace advice language patterns"""
        modifications = []
        result = text

        for pattern, replacement in self._compiled_advice:
            if pattern.search(result):
                result = pattern.sub(replacement, result)
                modifications.append(f"Replaced advice pattern: {pattern.pattern}")

        return result, modifications

    def _remove_opinion_patterns(self, text: str) -> Tuple[str, List[str]]:
        """Remove or replace opinion-as-fact patterns"""
        modifications = []
        result = text

        for pattern, replacement in self._compiled_opinion:
            if pattern.search(result):
                result = pattern.sub(replacement, result)
                modifications.append(f"Replaced opinion pattern: {pattern.pattern}")

        return result, modifications

    def _convert_certainty_language(self, text: str) -> Tuple[str, List[str]]:
        """Convert certainty language to descriptive language"""
        modifications = []
        result = text

        for pattern, replacement in self._compiled_certainty:
            if pattern.search(result):
                result = pattern.sub(replacement, result)
                modifications.append(f"Converted certainty pattern: {pattern.pattern}")

        return result, modifications

    def _ensure_descriptive_tone(self, text: str) -> Tuple[str, List[str]]:
        """
        Ensure text has descriptive-only tone

        Converts remaining prescriptive verbs to descriptive alternatives
        """
        modifications = []
        result = text

        # Generic prescriptive to descriptive conversions
        prescriptive_replacements: Dict[str, str] = {
            r"\bshould buy\b": "is available for purchase",
            r"\bshould sell\b": "is available for sale",
            r"\bshould invest\b": "presents investment opportunities",
            r"\bshould hold\b": "is currently held",
            r"\bshould consider\b": "may be considered",
            r"\bmust buy\b": "is available for purchase",
            r"\bmust sell\b": "is available for sale",
            r"\bneed to buy\b": "is available for purchase",
            r"\bneed to sell\b": "is available for sale",
            r"\bbetter to buy\b": "is available for purchase",
            r"\bbetter to sell\b": "is available for sale",
            r"\brecommend buying\b": "buying is an option",
            r"\brecommend selling\b": "selling is an option",
            r"\badvise buying\b": "buying is an option",
            r"\badvise selling\b": "selling is an option",
            r"\bsuggest buying\b": "buying is an option",
            r"\bsuggest selling\b": "selling is an option",
        }

        for pattern, replacement in prescriptive_replacements.items():
            compiled_pattern = re.compile(pattern, re.IGNORECASE)
            if compiled_pattern.search(result):
                result = compiled_pattern.sub(replacement, result)
                modifications.append(f"Converted prescriptive phrase: {pattern}")

        return result, modifications

    def _has_disclaimer(self, text: str) -> bool:
        """Check if text contains a required disclaimer"""
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in self.REQUIRED_DISCLAIMER_PHRASES)

    def _add_disclaimer(self, text: str, disclaimer: str) -> str:
        """Add disclaimer to text"""
        # Ensure proper spacing
        if text.endswith("\n\n"):
            return f"{text}{disclaimer}"
        elif text.endswith("\n"):
            return f"{text}\n{disclaimer}"
        else:
            return f"{text}\n\n{disclaimer}"

    def _calculate_confidence(self, violation_count: int, modification_count: int) -> float:
        """
        Calculate confidence score based on modifications

        Higher confidence = fewer modifications needed
        """
        if violation_count == 0 and modification_count == 0:
            return 1.0

        # Base confidence
        base_confidence = 0.95

        # Reduce for each violation/modification
        reduction_per_item = 0.05
        total_reduction = (violation_count + modification_count) * reduction_per_item

        return max(0.5, base_confidence - total_reduction)


# Global guardrail instance for convenience
compliance_guardrail = ComplianceGuardrail()
