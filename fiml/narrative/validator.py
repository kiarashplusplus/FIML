"""
Narrative Quality Validator

Validates generated narratives for compliance, quality, and safety.
Ensures narratives meet standards before being served to users.
"""

import re
from typing import List, Optional, Tuple

from fiml.core.logging import get_logger

logger = get_logger(__name__)


class NarrativeValidator:
    """
    Validates narrative quality and compliance

    Checks for:
    - Appropriate length
    - Presence of disclaimers
    - Absence of predictive/advice language
    - Readability
    - Factual accuracy
    """

    # Investment advice keywords that should be blocked
    ADVICE_KEYWORDS = [
        r"\bbuy\b",
        r"\bsell\b",
        r"\binvest\b",
        r"\brecommend(?:ed|ation)?\b",
        r"\bshould (?:buy|sell|invest)\b",
        r"\bmust (?:buy|sell)\b",
        r"\bwill (?:reach|hit|go to)\s*\$?\d+",
        r"\bprice target\b",
        r"\bstrong buy\b",
        r"\bstrong sell\b",
        r"\bhold\b.*\brating\b",
        r"\bupgrade(?:d)?\b",
        r"\bdowngrade(?:d)?\b",
    ]

    # Predictive language that should be flagged
    PREDICTIVE_KEYWORDS = [
        r"\bwill (?:increase|decrease|rise|fall|gain|lose)\b",
        r"\bgoing to\b",
        r"\bexpect(?:ed|ing)? to (?:reach|hit|climb)\b",
        r"\blikely to\b",
        r"\bpredicted? to\b",
        r"\bforecast(?:ed|ing)?\b",
        r"\bshould (?:reach|hit|climb|fall)\b",
    ]

    # Required disclaimer phrases (at least one must be present)
    REQUIRED_DISCLAIMERS = [
        "not financial advice",
        "not investment advice",
        "data analysis only",
        "informational purposes only",
        "past performance",
        # Spanish
        "no es asesoramiento financiero",
        "no es consejo de inversión",
        "solo proporciona análisis",
        "solo con fines informativos",
        # French
        "n'est pas un conseil financier",
        "n'est pas un conseil d'investissement",
        "analyse de données uniquement",
        "à des fins d'information uniquement",
    ]

    def __init__(self) -> None:
        """Initialize narrative validator"""
        logger.info("Narrative validator initialized")

    def validate(
        self,
        text: str,
        min_length: int = 50,
        max_length: int = 5000,
        source_data: Optional[dict] = None,
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Validate narrative comprehensively

        Args:
            text: Narrative text to validate
            min_length: Minimum character length
            max_length: Maximum character length
            source_data: Optional source data for fact-checking

        Returns:
            Tuple of (is_valid, errors, warnings)

        Example:
            >>> validator = NarrativeValidator()
            >>> is_valid, errors, warnings = validator.validate(narrative_text)
            >>> if not is_valid:
            ...     print(f"Validation failed: {errors}")
        """
        errors: List[str] = []
        warnings: List[str] = []

        # Length validation
        if not self.check_length(text, min_length, max_length):
            errors.append(f"Length must be between {min_length} and {max_length} characters")

        # Disclaimer validation
        if not self.check_disclaimer(text):
            errors.append("Missing required disclaimer")

        # Investment advice check
        if self.check_investment_advice(text):
            errors.append("Contains investment advice language")

        # Predictive language check
        predictions = self.check_predictions(text)
        if predictions:
            warnings.append(f"Contains predictive language: {', '.join(predictions)}")

        # Readability check
        readability = self.check_readability(text)
        if readability < 30:
            warnings.append(f"Low readability score: {readability:.1f}")

        # Factual accuracy (if source data provided)
        if source_data:
            accuracy_issues = self.check_factual_accuracy(text, source_data)
            if accuracy_issues:
                warnings.extend(accuracy_issues)

        is_valid = len(errors) == 0
        logger.info(
            "Narrative validated",
            is_valid=is_valid,
            errors=len(errors),
            warnings=len(warnings),
        )

        return is_valid, errors, warnings

    def check_length(self, text: str, min_length: int, max_length: int) -> bool:
        """
        Check if text meets length requirements

        Args:
            text: Text to check
            min_length: Minimum characters
            max_length: Maximum characters

        Returns:
            True if length is valid
        """
        length = len(text)
        return min_length <= length <= max_length

    def check_disclaimer(self, text: str) -> bool:
        """
        Check if text contains required disclaimer

        Args:
            text: Text to check

        Returns:
            True if disclaimer is present
        """
        text_lower = text.lower()
        return any(disclaimer in text_lower for disclaimer in self.REQUIRED_DISCLAIMERS)

    def check_investment_advice(self, text: str) -> bool:
        """
        Check if text contains investment advice language

        Args:
            text: Text to check

        Returns:
            True if advice language is detected (invalid)
        """
        text_lower = text.lower()
        for pattern in self.ADVICE_KEYWORDS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logger.warning(f"Investment advice detected: {pattern}")
                return True
        return False

    def check_predictions(self, text: str) -> List[str]:
        """
        Check for predictive language

        Args:
            text: Text to check

        Returns:
            List of detected predictive phrases
        """
        predictions = []
        text_lower = text.lower()

        for pattern in self.PREDICTIVE_KEYWORDS:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                predictions.extend(matches)

        return predictions

    def check_readability(self, text: str) -> float:
        """
        Calculate Flesch Reading Ease score

        Args:
            text: Text to analyze

        Returns:
            Readability score (0-100, higher is easier)

        Note:
            90-100: Very easy
            60-70: Plain English
            30-50: Difficult
            0-30: Very difficult
        """
        # Count sentences
        sentences = len(re.findall(r"[.!?]+", text))
        if sentences == 0:
            sentences = 1

        # Count words
        words = len(re.findall(r"\b\w+\b", text))
        if words == 0:
            return 0.0

        # Count syllables (approximation)
        syllables = self._count_syllables(text)

        # Flesch Reading Ease formula
        score = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)

        # Clamp between 0 and 100
        return max(0.0, min(100.0, score))

    def _count_syllables(self, text: str) -> int:
        """
        Approximate syllable count

        Args:
            text: Text to analyze

        Returns:
            Estimated syllable count
        """
        # Simple syllable counting: count vowel groups
        text = text.lower()
        syllables = 0
        vowels = "aeiouy"
        previous_was_vowel = False

        for char in text:
            is_vowel = char in vowels
            if is_vowel and not previous_was_vowel:
                syllables += 1
            previous_was_vowel = is_vowel

        # Adjust for silent 'e' at end of words
        words = re.findall(r"\b\w+\b", text)
        for word in words:
            if len(word) > 2 and word.endswith("e"):
                syllables -= 1

        return max(1, syllables)

    def check_factual_accuracy(self, text: str, source_data: dict) -> List[str]:
        """
        Check if narrative matches source data

        Args:
            text: Narrative text
            source_data: Source data dictionary

        Returns:
            List of accuracy issues found
        """
        issues: List[str] = []

        # Extract numerical values from text
        numbers_in_text = re.findall(r"\$?(\d+(?:\.\d+)?)", text)

        # Check price accuracy if provided
        if "price" in source_data:
            price = source_data["price"]
            price_str = f"{price:.2f}"
            if price_str.replace(".", "") not in "".join(numbers_in_text):
                # Allow for some rounding
                price_rounded = round(price, 1)
                price_rounded_str = f"{price_rounded:.1f}"
                if price_rounded_str.replace(".", "") not in "".join(numbers_in_text):
                    issues.append(f"Price in text may not match source: ${price}")

        # Check percentage accuracy if provided
        if "change_percent" in source_data:
            change_pct = source_data["change_percent"]
            # Look for percentage mentions
            pct_matches = re.findall(r"(\d+(?:\.\d+)?)%", text)
            if pct_matches:
                # Check if any match is close to source
                matches_found = any(abs(float(pct) - abs(change_pct)) < 0.5 for pct in pct_matches)
                if not matches_found:
                    issues.append(f"Change percent in text may not match source: {change_pct}%")

        # Check volume if provided (order of magnitude)
        if "volume" in source_data:
            volume = source_data["volume"]
            # Convert volume to magnitude (millions/billions)
            if volume > 1_000_000_000:
                magnitude = "billion"
            elif volume > 1_000_000:
                magnitude = "million"
            else:
                magnitude = ""

            if magnitude and magnitude not in text.lower():
                issues.append(f"Volume magnitude not mentioned: {magnitude}")

        return issues

    def auto_inject_disclaimer(self, text: str) -> str:
        """
        Automatically inject disclaimer if missing

        Args:
            text: Narrative text

        Returns:
            Text with disclaimer added if necessary
        """
        if self.check_disclaimer(text):
            return text

        # Add disclaimer at the end
        disclaimer = "\n\nThis is not financial advice. FIML provides data analysis only."
        logger.info("Auto-injecting disclaimer")
        return text + disclaimer

    def sanitize_narrative(self, text: str) -> str:
        """
        Remove or replace problematic content

        Args:
            text: Narrative text to sanitize

        Returns:
            Sanitized text

        Note:
            Removes investment advice language and predictive statements
        """
        sanitized = text

        # Replace advice keywords with neutral language
        replacements = {
            r"\b(should |must )?(buy|sell|invest in)\b": "consider",
            r"\brecommend(?:ed|ation)?\b": "note",
            r"\bstrong (buy|sell)\b": "notable",
            r"\bprice target\b": "price level",
            r"\bwill reach\b": "is at",
            r"\bwill (increase|rise|climb)\b": "has increased",
            r"\bwill (decrease|fall|drop)\b": "has decreased",
            r"\bgoing to\b": "currently",
            r"\bexpect(?:ed|ing)? to\b": "has",
            r"\blikely to\b": "has recently",
        }

        for pattern, replacement in replacements.items():
            before_replacement = sanitized
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
            if sanitized != before_replacement:
                logger.warning(f"Sanitized pattern: {pattern}")

        return sanitized

    def process_with_guardrail(
        self,
        text: str,
        asset_class: str = "equity",
        region: str = "US",
    ) -> Tuple[str, bool, List[str]]:
        """
        Process narrative through the compliance guardrail layer

        This is a convenience method that integrates the comprehensive
        ComplianceGuardrail with this validator.

        Args:
            text: Narrative text to process
            asset_class: Type of asset (equity, crypto, etc.)
            region: User's region (US, EU, UK, etc.)

        Returns:
            Tuple of (processed_text, is_compliant, violations_found)

        Example:
            >>> validator = NarrativeValidator()
            >>> text, compliant, violations = validator.process_with_guardrail(
            ...     "You should buy AAPL now!",
            ...     asset_class="equity",
            ...     region="US"
            ... )
            >>> print(compliant)
            True
            >>> print(violations)
            ['Prescriptive verb found: ...']
        """
        from fiml.compliance.disclaimers import AssetClass
        from fiml.compliance.guardrail import ComplianceGuardrail
        from fiml.compliance.router import Region

        # Map string to enum
        try:
            asset_enum = AssetClass(asset_class.lower())
        except ValueError:
            asset_enum = AssetClass.EQUITY

        try:
            region_enum = Region(region.upper())
        except ValueError:
            region_enum = Region.US

        # Process through guardrail
        guardrail = ComplianceGuardrail()
        result = guardrail.process(
            text,
            asset_class=asset_enum,
            region=region_enum,
        )

        return result.processed_text, result.is_compliant, result.violations_found


# Global validator instance
narrative_validator = NarrativeValidator()
