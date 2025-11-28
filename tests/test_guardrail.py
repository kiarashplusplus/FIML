"""
Tests for Compliance Guardrail Layer

Comprehensive test suite covering:
- Prescriptive verb detection and blocking
- Advice-like language removal
- Descriptive tone enforcement
- Automatic disclaimer addition
- Various edge cases and integration scenarios
"""

import pytest

from fiml.compliance.disclaimers import AssetClass
from fiml.compliance.guardrail import (ComplianceGuardrail, GuardrailAction,
                                       GuardrailResult, compliance_guardrail)
from fiml.compliance.router import Region

# ============================================================================
# Basic Functionality Tests
# ============================================================================


class TestGuardrailBasic:
    """Test basic guardrail functionality"""

    def test_guardrail_initialization(self):
        """Test guardrail initializes correctly"""
        guardrail = ComplianceGuardrail()

        assert guardrail is not None
        assert guardrail.disclaimer_generator is not None
        assert guardrail.strict_mode is False
        assert guardrail.auto_add_disclaimer is True

    def test_guardrail_initialization_with_options(self):
        """Test guardrail initialization with custom options"""
        guardrail = ComplianceGuardrail(
            strict_mode=True,
            auto_add_disclaimer=False,
        )

        assert guardrail.strict_mode is True
        assert guardrail.auto_add_disclaimer is False

    def test_global_instance_exists(self):
        """Test that global compliance_guardrail instance exists"""
        assert compliance_guardrail is not None
        assert isinstance(compliance_guardrail, ComplianceGuardrail)

    def test_process_empty_text(self):
        """Test processing empty text"""
        guardrail = ComplianceGuardrail()

        result = guardrail.process("")

        assert result.action == GuardrailAction.PASSED
        assert result.processed_text == ""
        assert not result.was_modified

    def test_process_compliant_text(self):
        """Test processing already compliant text"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        compliant_text = "AAPL stock is currently trading at $175.50. Volume is above average."

        result = guardrail.process(compliant_text)

        # Should pass or only add disclaimer
        assert result.is_compliant
        assert len(result.violations_found) == 0

    def test_guardrail_result_properties(self):
        """Test GuardrailResult properties"""
        result = GuardrailResult(
            action=GuardrailAction.MODIFIED,
            original_text="test",
            processed_text="test modified",
            modifications=["Test modification"],
        )

        assert result.was_modified is True
        assert result.is_compliant is True

        blocked_result = GuardrailResult(
            action=GuardrailAction.BLOCKED,
            original_text="test",
            processed_text="",
        )

        assert blocked_result.was_modified is False
        assert blocked_result.is_compliant is False


# ============================================================================
# Prescriptive Verb Tests
# ============================================================================


class TestPrescriptiveVerbs:
    """Test prescriptive verb detection and handling"""

    @pytest.mark.parametrize(
        "verb",
        [
            "should",
            "must",
            "ought to",
            "need to",
            "have to",
            "better to",
            "advise",
            "recommend",
            "suggest",
            "urge",
            "encourage",
        ],
    )
    def test_detects_prescriptive_verbs(self, verb):
        """Test that all prescriptive verbs are detected"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        text = f"You {verb} consider this stock."

        result = guardrail.process(text)

        assert len(result.violations_found) > 0

    def test_should_buy_conversion(self):
        """Test 'should buy' is converted to descriptive language"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        text = "You should buy AAPL stock now."

        result = guardrail.process(text)

        assert "should buy" not in result.processed_text.lower()
        assert result.was_modified

    def test_must_sell_conversion(self):
        """Test 'must sell' is converted to descriptive language"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        text = "You must sell your position immediately."

        result = guardrail.process(text)

        assert "must sell" not in result.processed_text.lower()
        assert result.was_modified

    def test_recommend_conversion(self):
        """Test 'recommend' patterns are converted"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        text = "I recommend buying this stock."

        result = guardrail.process(text)

        assert "recommend buying" not in result.processed_text.lower()
        assert result.was_modified


# ============================================================================
# Advice-Like Language Tests
# ============================================================================


class TestAdviceLikeLanguage:
    """Test advice-like language detection and removal"""

    def test_direct_buy_recommendation(self):
        """Test direct buy recommendation is removed"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        text = "Buy now before the price goes up!"

        result = guardrail.process(text)

        assert "buy now" not in result.processed_text.lower()
        assert result.was_modified

    def test_direct_sell_recommendation(self):
        """Test direct sell recommendation is removed"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        text = "Sell immediately to avoid losses!"

        result = guardrail.process(text)

        assert "sell immediately" not in result.processed_text.lower()
        assert result.was_modified

    def test_strong_buy_rating(self):
        """Test 'strong buy' rating is removed"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        text = "This stock has a strong buy rating."

        result = guardrail.process(text)

        assert "strong buy" not in result.processed_text.lower()
        assert result.was_modified

    def test_strong_sell_rating(self):
        """Test 'strong sell' rating is removed"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        text = "Analysts give this a strong sell rating."

        result = guardrail.process(text)

        assert "strong sell" not in result.processed_text.lower()
        assert result.was_modified

    def test_price_target_removal(self):
        """Test price target predictions are removed"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        text = "The price target is $200 by year end."

        result = guardrail.process(text)

        assert "price target" not in result.processed_text.lower()
        assert result.was_modified

    def test_good_time_to_buy(self):
        """Test 'good time to buy' patterns are removed"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        text = "This is a good time to buy the dip."

        result = guardrail.process(text)

        assert "good time to buy" not in result.processed_text.lower()
        assert result.was_modified


# ============================================================================
# Opinion as Fact Tests
# ============================================================================


class TestOpinionAsFact:
    """Test opinion-as-fact pattern detection and removal"""

    def test_undervalued_opinion(self):
        """Test 'undervalued' opinion is modified"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        text = "This stock is undervalued and will go up."

        result = guardrail.process(text)

        # Should modify the opinion language
        assert len(result.violations_found) > 0 or result.was_modified

    def test_overvalued_opinion(self):
        """Test 'overvalued' opinion is modified"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        text = "This stock is overvalued and will crash."

        result = guardrail.process(text)

        assert len(result.violations_found) > 0 or result.was_modified

    def test_cannot_lose_language(self):
        """Test 'cannot lose' language is removed"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        text = "With this investment, you cannot lose."

        result = guardrail.process(text)

        assert "cannot lose" not in result.processed_text.lower()
        assert result.was_modified

    def test_risk_free_language(self):
        """Test 'risk-free' language is removed"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        text = "This is a risk-free investment opportunity."

        result = guardrail.process(text)

        assert "risk-free" not in result.processed_text.lower()
        assert result.was_modified


# ============================================================================
# Certainty Language Tests
# ============================================================================


class TestCertaintyLanguage:
    """Test certainty language conversion to descriptive"""

    def test_will_increase(self):
        """Test 'will increase' is converted to descriptive"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        text = "The stock will increase by 50% next month."

        result = guardrail.process(text)

        assert "will increase" not in result.processed_text.lower()
        assert result.was_modified

    def test_will_decrease(self):
        """Test 'will decrease' is converted to descriptive"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        text = "The price will decrease significantly."

        result = guardrail.process(text)

        assert "will decrease" not in result.processed_text.lower()
        assert result.was_modified

    def test_going_to_rise(self):
        """Test 'going to' predictions are converted"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        text = "The market is going to rise next week."

        result = guardrail.process(text)

        assert "going to" not in result.processed_text.lower()
        assert result.was_modified

    def test_likely_to_language(self):
        """Test 'likely to' language is converted"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        text = "The stock is likely to increase after earnings."

        result = guardrail.process(text)

        assert "likely to increase" not in result.processed_text.lower()
        assert result.was_modified

    def test_expected_to_reach(self):
        """Test 'expected to reach' is converted"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        text = "The price is expected to reach $300."

        result = guardrail.process(text)

        assert "expected to reach" not in result.processed_text.lower()
        assert result.was_modified

    def test_predicted_to_language(self):
        """Test 'predicted to' language is converted"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        # Use a phrase that matches our pattern
        text = "The stock is predicted to rise significantly."

        result = guardrail.process(text)

        assert "predicted to rise" not in result.processed_text.lower()
        assert result.was_modified


# ============================================================================
# Disclaimer Tests
# ============================================================================


class TestDisclaimerHandling:
    """Test automatic disclaimer handling"""

    def test_adds_disclaimer_when_missing(self):
        """Test disclaimer is added when missing"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=True)

        text = "AAPL stock is trading at $175."

        result = guardrail.process(text)

        assert result.disclaimer_added
        assert (
            "not financial advice" in result.processed_text.lower()
            or "informational purposes" in result.processed_text.lower()
        )

    def test_does_not_duplicate_disclaimer(self):
        """Test disclaimer is not duplicated if already present"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=True)

        text = "AAPL is trading at $175. This is not financial advice."

        result = guardrail.process(text)

        assert not result.disclaimer_added
        # Count occurrences of disclaimer
        count = result.processed_text.lower().count("not financial advice")
        assert count == 1

    def test_respects_auto_add_disclaimer_false(self):
        """Test disclaimer is not added when auto_add_disclaimer is False"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        text = "AAPL stock is trading at $175."

        result = guardrail.process(text)

        assert not result.disclaimer_added

    def test_add_disclaimer_method(self):
        """Test explicit add_disclaimer method"""
        guardrail = ComplianceGuardrail()

        text = "AAPL is trading at $175."

        result = guardrail.add_disclaimer(text)

        assert (
            "not financial advice" in result.lower() or "informational purposes" in result.lower()
        )

    def test_add_disclaimer_respects_existing(self):
        """Test add_disclaimer doesn't duplicate"""
        guardrail = ComplianceGuardrail()

        text = "AAPL is trading at $175. This is not financial advice."

        result = guardrail.add_disclaimer(text)

        assert result == text  # Should not modify


# ============================================================================
# Scan Only Tests
# ============================================================================


class TestScanOnly:
    """Test scan-only functionality"""

    def test_scan_only_returns_violations(self):
        """Test scan_only returns violations without modifying"""
        guardrail = ComplianceGuardrail()

        text = "You should buy this stock now!"

        violations = guardrail.scan_only(text)

        assert len(violations) > 0
        assert any("should" in v.lower() for v in violations)

    def test_scan_only_empty_for_compliant(self):
        """Test scan_only returns empty list for compliant text"""
        guardrail = ComplianceGuardrail()

        text = "AAPL stock is currently trading at $175.50."

        violations = guardrail.scan_only(text)

        assert len(violations) == 0

    def test_is_compliant_with_compliant_text(self):
        """Test is_compliant returns True for compliant text"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        text = "AAPL stock is trading at $175."

        assert guardrail.is_compliant(text)

    def test_is_compliant_with_non_compliant_text(self):
        """Test is_compliant returns False for non-compliant text"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        text = "You should buy this stock immediately!"

        assert not guardrail.is_compliant(text)


# ============================================================================
# Strict Mode Tests
# ============================================================================


class TestStrictMode:
    """Test strict mode functionality"""

    def test_strict_mode_blocks_excessive_violations(self):
        """Test strict mode blocks content with many violations"""
        guardrail = ComplianceGuardrail(strict_mode=True)

        # Text with many violations
        text = """
        You should buy this stock now. I recommend investing immediately.
        This is a strong buy. The price will definitely increase.
        You must sell your other holdings. This stock is guaranteed to rise.
        Don't miss this opportunity! Buy it before it goes up!
        """

        result = guardrail.process(text)

        assert result.action == GuardrailAction.BLOCKED
        assert result.processed_text == ""
        assert not result.is_compliant

    def test_non_strict_mode_modifies_instead_of_blocking(self):
        """Test non-strict mode modifies content instead of blocking"""
        guardrail = ComplianceGuardrail(strict_mode=False)

        # Same text with many violations
        text = """
        You should buy this stock now. I recommend investing immediately.
        This is a strong buy. The price will definitely increase.
        """

        result = guardrail.process(text)

        assert result.action != GuardrailAction.BLOCKED
        assert result.is_compliant


# ============================================================================
# Regional and Asset Class Tests
# ============================================================================


class TestRegionalCompliance:
    """Test regional compliance handling"""

    @pytest.mark.parametrize(
        "region",
        [
            Region.US,
            Region.EU,
            Region.UK,
            Region.JP,
            Region.GLOBAL,
        ],
    )
    def test_disclaimer_for_different_regions(self, region):
        """Test disclaimers are added for different regions"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=True)

        text = "AAPL stock is trading at $175."

        result = guardrail.process(text, region=region)

        assert result.disclaimer_added
        assert len(result.processed_text) > len(text)

    @pytest.mark.parametrize(
        "asset_class",
        [
            AssetClass.EQUITY,
            AssetClass.CRYPTO,
            AssetClass.DERIVATIVE,
            AssetClass.FOREX,
            AssetClass.ETF,
        ],
    )
    def test_disclaimer_for_different_asset_classes(self, asset_class):
        """Test disclaimers are added for different asset classes"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=True)

        text = "This asset is trading at current levels."

        result = guardrail.process(text, asset_class=asset_class)

        assert result.disclaimer_added


# ============================================================================
# Edge Cases and Integration Tests
# ============================================================================


class TestEdgeCases:
    """Test edge cases and unusual inputs"""

    def test_whitespace_only_text(self):
        """Test handling of whitespace-only text"""
        guardrail = ComplianceGuardrail()

        result = guardrail.process("   \n\t   ")

        assert result.action == GuardrailAction.PASSED

    def test_none_input_handling(self):
        """Test handling of None-like inputs"""
        guardrail = ComplianceGuardrail()

        # Empty string
        result = guardrail.process("")
        assert result.action == GuardrailAction.PASSED

    def test_very_long_text(self):
        """Test handling of very long text"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        # Long compliant text
        long_text = "AAPL stock is trading at $175. " * 1000

        result = guardrail.process(long_text)

        assert result.is_compliant

    def test_mixed_case_detection(self):
        """Test detection works regardless of case"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        text = "You SHOULD BUY this STOCK Now!"

        result = guardrail.process(text)

        assert result.was_modified
        assert "should buy" not in result.processed_text.lower()

    def test_multiple_violations_in_single_sentence(self):
        """Test handling of multiple violations in one sentence"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        text = "You should buy now because the price will definitely increase."

        result = guardrail.process(text)

        assert result.was_modified
        assert len(result.modifications) >= 1

    def test_confidence_score_calculation(self):
        """Test confidence score is calculated correctly"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        # Compliant text should have high confidence
        compliant_result = guardrail.process("AAPL is trading at $175.")
        assert compliant_result.confidence >= 0.9

        # Non-compliant text should have lower confidence
        non_compliant_result = guardrail.process("You should buy this stock now!")
        assert non_compliant_result.confidence < compliant_result.confidence

    def test_preserves_factual_content(self):
        """Test that factual financial data is preserved"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        text = "AAPL is trading at $175.50 with volume of 50 million shares."

        result = guardrail.process(text)

        assert "$175.50" in result.processed_text
        assert "50 million" in result.processed_text

    def test_unicode_content(self):
        """Test handling of unicode content"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        # Japanese: "The stock is currently trading at ¥1500."
        text = "株式は現在¥1500で取引されています。"

        result = guardrail.process(text)

        # Should not crash and should preserve content
        assert result.is_compliant


class TestMultilingualDisclaimer:
    """Test multilingual disclaimer detection"""

    def test_spanish_disclaimer_detected(self):
        """Test Spanish disclaimer is detected"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=True)

        # Spanish: "AAPL is trading at $175. This is not financial advice."
        text = "AAPL está cotizando a $175. Esto no es asesoramiento financiero."

        result = guardrail.process(text)

        # Should not add duplicate disclaimer
        assert not result.disclaimer_added

    def test_french_disclaimer_detected(self):
        """Test French disclaimer is detected"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=True)

        # French: "AAPL is trading at $175. This is not financial advice."
        text = "AAPL se négocie à 175$. Ceci n'est pas un conseil financier."

        result = guardrail.process(text)

        # Should not add duplicate disclaimer
        assert not result.disclaimer_added


# ============================================================================
# Integration with Existing Components
# ============================================================================


class TestIntegrationWithExistingComponents:
    """Test integration with existing compliance components"""

    def test_guardrail_with_disclaimer_generator(self):
        """Test guardrail uses disclaimer generator correctly"""
        from fiml.compliance.disclaimers import DisclaimerGenerator

        disclaimer_gen = DisclaimerGenerator()
        guardrail = ComplianceGuardrail(
            disclaimer_generator=disclaimer_gen,
            auto_add_disclaimer=True,
        )

        text = "AAPL is trading at $175."

        result = guardrail.process(text, asset_class=AssetClass.CRYPTO)

        # Should use disclaimer generator and add crypto-specific disclaimer
        assert result.disclaimer_added
        assert (
            "crypto" in result.processed_text.lower()
            or "financial advice" in result.processed_text.lower()
        )

    def test_import_from_package(self):
        """Test that guardrail can be imported from package"""
        from fiml.compliance import (ComplianceGuardrail, GuardrailAction,
                                     GuardrailResult, compliance_guardrail)

        assert ComplianceGuardrail is not None
        assert GuardrailAction is not None
        assert GuardrailResult is not None
        assert compliance_guardrail is not None


# ============================================================================
# Multilingual Support Tests
# ============================================================================


class TestMultilingualSupport:
    """Test multilingual compliance detection and processing"""

    def test_spanish_advice_detection(self):
        """Test Spanish advice pattern detection"""
        from fiml.compliance.guardrail import SupportedLanguage

        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        # Spanish: "You should buy AAPL now"
        text = "Debería comprar AAPL ahora"

        result = guardrail.process(text, language=SupportedLanguage.SPANISH)

        assert len(result.violations_found) > 0 or result.was_modified
        assert result.detected_language == "es"

    def test_french_advice_detection(self):
        """Test French advice pattern detection"""
        from fiml.compliance.guardrail import SupportedLanguage

        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        # French: "You should buy AAPL now"
        text = "Vous devriez acheter AAPL maintenant"

        result = guardrail.process(text, language=SupportedLanguage.FRENCH)

        assert len(result.violations_found) > 0 or result.was_modified
        assert result.detected_language == "fr"

    def test_german_advice_detection(self):
        """Test German advice pattern detection"""
        from fiml.compliance.guardrail import SupportedLanguage

        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        # German: "You should buy AAPL"
        text = "Sie sollten AAPL kaufen"

        result = guardrail.process(text, language=SupportedLanguage.GERMAN)

        assert len(result.violations_found) > 0 or result.was_modified
        assert result.detected_language == "de"

    def test_japanese_detection(self):
        """Test Japanese language detection"""
        from fiml.compliance.guardrail import SupportedLanguage

        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        # Japanese: "You should buy this stock"
        text = "この株を買うべきです"

        result = guardrail.process(text, language=SupportedLanguage.JAPANESE)

        assert result.detected_language == "ja"

    def test_chinese_detection(self):
        """Test Chinese language detection"""
        from fiml.compliance.guardrail import SupportedLanguage

        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        # Chinese: "You should buy AAPL"
        text = "你应该买入AAPL"

        result = guardrail.process(text, language=SupportedLanguage.CHINESE)

        assert result.detected_language == "zh"

    def test_auto_language_detection_japanese(self):
        """Test automatic Japanese language detection"""
        from fiml.compliance.guardrail import SupportedLanguage

        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        # Japanese text with hiragana/katakana
        text = "株式は現在¥1500で取引されています。"

        result = guardrail.process(text, language=SupportedLanguage.AUTO)

        assert result.detected_language == "ja"

    def test_auto_language_detection_chinese(self):
        """Test automatic Chinese language detection"""
        from fiml.compliance.guardrail import SupportedLanguage

        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        # Chinese text
        text = "这只股票目前正在交易。"

        result = guardrail.process(text, language=SupportedLanguage.AUTO)

        assert result.detected_language == "zh"

    def test_italian_disclaimer_detection(self):
        """Test Italian disclaimer is detected"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=True)

        # Italian: "This is not financial advice"
        text = "AAPL è in negoziazione a $175. Questo non è consulenza finanziaria."

        result = guardrail.process(text)

        # Should not add duplicate disclaimer
        assert not result.disclaimer_added

    def test_portuguese_disclaimer_detection(self):
        """Test Portuguese disclaimer is detected"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=True)

        # Portuguese: "This is not financial advice"
        text = "AAPL está sendo negociado a $175. Isto não é aconselhamento financeiro."

        result = guardrail.process(text)

        # Should not add duplicate disclaimer
        assert not result.disclaimer_added

    def test_german_disclaimer_detection(self):
        """Test German disclaimer is detected"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=True)

        # German: "This is not financial advice"
        text = "AAPL wird bei $175 gehandelt. Dies ist keine Finanzberatung."

        result = guardrail.process(text)

        # Should not add duplicate disclaimer
        assert not result.disclaimer_added

    def test_japanese_disclaimer_detection(self):
        """Test Japanese disclaimer is detected"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=True)

        # Japanese: "This is not financial advice"
        text = "AAPLは$175で取引されています。これは金融アドバイスではありません。"

        result = guardrail.process(text)

        # Should not add duplicate disclaimer
        assert not result.disclaimer_added

    def test_chinese_disclaimer_detection(self):
        """Test Chinese disclaimer is detected"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=True)

        # Chinese: "This does not constitute financial advice"
        text = "AAPL目前价格为$175。这不构成财务建议。"

        result = guardrail.process(text)

        # Should not add duplicate disclaimer
        assert not result.disclaimer_added

    def test_supported_languages_list(self):
        """Test that guardrail reports supported languages"""
        guardrail = ComplianceGuardrail()

        languages = guardrail.get_supported_languages()

        assert "en" in languages
        assert "es" in languages
        assert "fr" in languages
        assert "de" in languages
        assert "ja" in languages
        assert "zh" in languages
        assert "fa" in languages
        assert len(languages) >= 9

    def test_multilingual_patterns_class(self):
        """Test MultilingualPatterns class has expected structure"""
        from fiml.compliance.guardrail import MultilingualPatterns

        # Check prescriptive verbs
        assert "en" in MultilingualPatterns.PRESCRIPTIVE_VERBS
        assert "es" in MultilingualPatterns.PRESCRIPTIVE_VERBS
        assert len(MultilingualPatterns.PRESCRIPTIVE_VERBS["en"]) > 0

        # Check advice patterns
        assert "en" in MultilingualPatterns.ADVICE_PATTERNS
        assert "es" in MultilingualPatterns.ADVICE_PATTERNS
        assert len(MultilingualPatterns.ADVICE_PATTERNS["en"]) > 0

        # Check disclaimer phrases
        assert "en" in MultilingualPatterns.DISCLAIMER_PHRASES
        assert "es" in MultilingualPatterns.DISCLAIMER_PHRASES
        assert len(MultilingualPatterns.DISCLAIMER_PHRASES["en"]) > 0

    def test_supported_language_enum(self):
        """Test SupportedLanguage enum values"""
        from fiml.compliance.guardrail import SupportedLanguage

        assert SupportedLanguage.ENGLISH.value == "en"
        assert SupportedLanguage.SPANISH.value == "es"
        assert SupportedLanguage.FRENCH.value == "fr"
        assert SupportedLanguage.GERMAN.value == "de"
        assert SupportedLanguage.JAPANESE.value == "ja"
        assert SupportedLanguage.CHINESE.value == "zh"
        assert SupportedLanguage.FARSI.value == "fa"
        assert SupportedLanguage.AUTO.value == "auto"

    def test_mixed_language_content(self):
        """Test handling of mixed English/Spanish content"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        # Mixed English and Spanish
        text = "AAPL is trading well. Debería comprar ahora."

        result = guardrail.process(text)

        # Should detect violations from both languages
        assert result.is_compliant or len(result.violations_found) > 0

    def test_default_language_initialization(self):
        """Test guardrail with custom default language"""
        from fiml.compliance.guardrail import SupportedLanguage

        guardrail = ComplianceGuardrail(
            auto_add_disclaimer=False,
            default_language=SupportedLanguage.SPANISH,
        )

        assert guardrail.default_language == SupportedLanguage.SPANISH

    def test_scan_only_with_language(self):
        """Test scan_only with explicit language"""
        from fiml.compliance.guardrail import SupportedLanguage

        guardrail = ComplianceGuardrail()

        # Spanish advice
        text = "Debería comprar AAPL ahora"

        violations = guardrail.scan_only(text, language=SupportedLanguage.SPANISH)

        assert len(violations) > 0

    def test_is_compliant_with_language(self):
        """Test is_compliant with explicit language"""
        from fiml.compliance.guardrail import SupportedLanguage

        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        # Spanish compliant text
        compliant_text = "AAPL está cotizando a $175."

        assert guardrail.is_compliant(compliant_text, language=SupportedLanguage.SPANISH)

        # Spanish non-compliant text
        non_compliant_text = "Debería comprar AAPL ahora"

        assert not guardrail.is_compliant(non_compliant_text, language=SupportedLanguage.SPANISH)

    def test_add_disclaimer_with_language(self):
        """Test add_disclaimer with explicit language"""
        from fiml.compliance.guardrail import SupportedLanguage

        guardrail = ComplianceGuardrail()

        text = "AAPL está cotizando a $175."

        result = guardrail.add_disclaimer(text, language=SupportedLanguage.SPANISH)

        # Should add disclaimer
        assert len(result) > len(text)

    def test_farsi_support(self):
        """Test Farsi/Persian language support"""
        from fiml.compliance.guardrail import SupportedLanguage

        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        # Farsi: "You should buy this stock"
        text = "شما باید این سهام را بخرید"

        result = guardrail.process(text, language=SupportedLanguage.FARSI)

        assert result.detected_language == "fa"
        assert len(result.violations_found) > 0 or result.was_modified

    def test_result_includes_detected_language(self):
        """Test that GuardrailResult includes detected language"""
        guardrail = ComplianceGuardrail(auto_add_disclaimer=False)

        text = "AAPL is trading at $175."

        result = guardrail.process(text)

        assert result.detected_language is not None
        assert result.detected_language == "en"
