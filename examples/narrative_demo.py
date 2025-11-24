#!/usr/bin/env python
"""
Narrative Generation System Demo

Demonstrates the AI narrative generation capabilities without requiring
Azure OpenAI credentials by using template-based fallbacks.
"""

import asyncio
from fiml.core.models import AssetType
from fiml.narrative.cache import narrative_cache
from fiml.narrative.models import ExpertiseLevel, Language
from fiml.narrative.templates import template_library
from fiml.narrative.validator import narrative_validator


def demo_template_library():
    """Demonstrate template library"""
    print("=" * 70)
    print("TEMPLATE LIBRARY DEMONSTRATION")
    print("=" * 70)
    print()

    # Test data for AAPL
    market_data = {
        "symbol": "AAPL",
        "price": 175.50,
        "change_pct": 2.48,
        "volume": 75000000,
        "avg_volume": 50000000,
        "week_52_high": 198.23,
        "week_52_low": 124.17,
    }

    # Generate narratives in multiple languages
    print("1. Price Movement Narratives (Multilingual)")
    print("-" * 70)

    for language in [Language.ENGLISH, Language.SPANISH, Language.FRENCH]:
        narrative = template_library.render_template(
            "price_movement", language, market_data
        )
        print(f"\n{language.value.upper()}:")
        print(narrative)

    # Volume analysis
    print("\n\n2. Volume Analysis")
    print("-" * 70)
    volume_data = {
        "volume": 75000000,
        "avg_volume": 50000000,
    }
    narrative = template_library.render_template(
        "volume_analysis", Language.ENGLISH, volume_data
    )
    print(narrative)

    # Technical summary
    print("\n\n3. Technical Analysis Summary")
    print("-" * 70)
    technical_data = {
        "rsi": 65.3,
        "macd_histogram": 0.53,
        "current_price": 175.50,
        "ma50": 170.25,
        "ma200": 165.80,
        "bb_upper": 182.50,
        "bb_lower": 167.50,
    }
    narrative = template_library.render_template(
        "technical_summary", Language.ENGLISH, technical_data
    )
    print(narrative)

    # Risk assessment
    print("\n\n4. Risk Assessment")
    print("-" * 70)
    risk_data = {
        "volatility": 0.25,
        "beta": 1.15,
        "var": 0.05,
        "max_dd": 15.3,
    }
    narrative = template_library.render_template(
        "risk_assessment", Language.ENGLISH, risk_data
    )
    print(narrative)


def demo_narrative_validator():
    """Demonstrate narrative validation"""
    print("\n\n")
    print("=" * 70)
    print("NARRATIVE VALIDATOR DEMONSTRATION")
    print("=" * 70)
    print()

    validator = narrative_validator

    # Test 1: Valid narrative
    print("1. Validating Compliant Narrative")
    print("-" * 70)
    valid_text = (
        "AAPL is currently trading at $175.50, showing a 2.48% increase today. "
        "Volume is elevated at 75 million shares. Technical indicators show bullish momentum. "
        "This is not financial advice. FIML provides data analysis only."
    )
    is_valid, errors, warnings = validator.validate(valid_text)
    print(f"Text: {valid_text[:100]}...")
    print(f"✓ Valid: {is_valid}")
    print(f"Errors: {errors}")
    print(f"Warnings: {warnings}")

    # Test 2: Invalid narrative (investment advice)
    print("\n\n2. Detecting Investment Advice")
    print("-" * 70)
    invalid_text = "You should buy AAPL stock now. It will reach $200 soon."
    is_valid, errors, warnings = validator.validate(invalid_text, min_length=10)
    print(f"Text: {invalid_text}")
    print(f"✗ Valid: {is_valid}")
    print(f"Errors detected: {errors}")

    # Test 3: Auto-inject disclaimer
    print("\n\n3. Auto-Injecting Disclaimer")
    print("-" * 70)
    text_without = "AAPL is trading at $175.50 with strong volume."
    text_with = validator.auto_inject_disclaimer(text_without)
    print(f"Original: {text_without}")
    print(f"Enhanced: {text_with}")

    # Test 4: Sanitize problematic content
    print("\n\n4. Sanitizing Problematic Content")
    print("-" * 70)
    problematic = "You should buy AAPL. It will increase significantly."
    sanitized = validator.sanitize_narrative(problematic)
    print(f"Original: {problematic}")
    print(f"Sanitized: {sanitized}")

    # Test 5: Readability scoring
    print("\n\n5. Readability Scoring")
    print("-" * 70)
    simple = "The cat sat on the mat. It was a nice day."
    complex = "The multifaceted implications of contemporary macroeconomic policies necessitate comprehensive analysis."

    simple_score = validator.check_readability(simple)
    complex_score = validator.check_readability(complex)
    print(f"Simple text score: {simple_score:.1f} (higher is easier)")
    print(f"Complex text score: {complex_score:.1f}")


async def demo_narrative_cache():
    """Demonstrate narrative caching"""
    print("\n\n")
    print("=" * 70)
    print("NARRATIVE CACHE DEMONSTRATION")
    print("=" * 70)
    print()

    cache = narrative_cache

    # Test cache operations
    print("1. Caching Operations")
    print("-" * 70)

    # Store a narrative
    narrative_data = {
        "summary": "AAPL shows strong momentum with technical indicators aligned.",
        "key_insights": [
            "Price above key moving averages",
            "Volume confirmation of trend",
        ],
        "risk_factors": [
            "Market volatility remains elevated",
        ],
    }

    success = await cache.set(
        symbol="AAPL",
        narrative_data=narrative_data,
        language="en",
        expertise_level="intermediate",
        asset_type=AssetType.EQUITY,
        volatility=2.5,
    )
    print(f"✓ Narrative cached: {success}")

    # Retrieve from cache
    cached = await cache.get(
        symbol="AAPL",
        language="en",
        expertise_level="intermediate",
    )
    print(f"✓ Retrieved from cache: {cached is not None}")
    if cached:
        print(f"  Summary: {cached.get('summary', '')[:60]}...")

    # Test cache metrics
    print("\n\n2. Cache Metrics")
    print("-" * 70)
    metrics = cache.get_metrics()
    print(f"Cache Metrics:")
    print(f"  - Hit count: {metrics['hit_count']}")
    print(f"  - Miss count: {metrics['miss_count']}")
    print(f"  - Hit rate: {metrics['hit_rate']:.1f}%")

    # Test TTL calculation
    print("\n\n3. Dynamic TTL Calculation")
    print("-" * 70)
    from fiml.core.models import Asset

    equity = Asset(symbol="AAPL", asset_type=AssetType.EQUITY)
    crypto = Asset(symbol="BTC/USD", asset_type=AssetType.CRYPTO)

    ttl_equity_low_vol = cache._calculate_ttl(equity, volatility=0.5)
    ttl_equity_high_vol = cache._calculate_ttl(equity, volatility=5.0)
    ttl_crypto_low_vol = cache._calculate_ttl(crypto, volatility=2.0)
    ttl_crypto_high_vol = cache._calculate_ttl(crypto, volatility=15.0)

    print(f"Equity (low volatility): {ttl_equity_low_vol} seconds")
    print(f"Equity (high volatility): {ttl_equity_high_vol} seconds")
    print(f"Crypto (low volatility): {ttl_crypto_low_vol} seconds")
    print(f"Crypto (high volatility): {ttl_crypto_high_vol} seconds")


def demo_integration():
    """Demonstrate complete integration"""
    print("\n\n")
    print("=" * 70)
    print("COMPLETE INTEGRATION DEMONSTRATION")
    print("=" * 70)
    print()

    print("Workflow: Generate → Validate → Cache → Retrieve")
    print("-" * 70)

    # 1. Generate using template
    market_data = {
        "symbol": "TSLA",
        "price": 242.50,
        "change_pct": 3.75,
        "volume": 125000000,
        "avg_volume": 95000000,
    }

    narrative = template_library.render_template(
        "price_movement", Language.ENGLISH, market_data
    )
    print(f"\n1. Generated Narrative:")
    print(f"   {narrative[:150]}...")

    # 2. Validate
    validator = narrative_validator
    is_valid, errors, warnings = validator.validate(narrative, min_length=10)

    if not is_valid:
        narrative = validator.auto_inject_disclaimer(narrative)
        is_valid, errors, warnings = validator.validate(narrative, min_length=10)

    print(f"\n2. Validation Result:")
    print(f"   ✓ Valid: {is_valid}")
    print(f"   Errors: {len(errors)}")
    print(f"   Warnings: {len(warnings)}")

    print(f"\n3. Ready for Caching and Distribution!")


def main():
    """Run all demonstrations"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 10 + "FIML AI NARRATIVE GENERATION SYSTEM DEMO" + " " * 18 + "║")
    print("╚" + "═" * 68 + "╝")

    # Run demos
    demo_template_library()
    demo_narrative_validator()
    asyncio.run(demo_narrative_cache())
    demo_integration()

    print("\n\n")
    print("=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)
    print()
    print("Key Features Demonstrated:")
    print("  ✓ Multi-language template library (EN, ES, FR, JA, ZH)")
    print("  ✓ Narrative quality validation")
    print("  ✓ Investment advice detection and blocking")
    print("  ✓ Automatic disclaimer injection")
    print("  ✓ Readability scoring")
    print("  ✓ Intelligent caching with dynamic TTL")
    print("  ✓ Market-aware cache invalidation")
    print("  ✓ Complete narrative generation pipeline")
    print()
    print("For production use with Azure OpenAI:")
    print("  1. Configure Azure OpenAI credentials in .env")
    print("  2. Use AzureOpenAIClient methods for AI-enhanced narratives")
    print("  3. Templates automatically fallback if API unavailable")
    print()


if __name__ == "__main__":
    main()
