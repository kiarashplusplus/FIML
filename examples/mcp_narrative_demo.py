"""
Example: MCP Narrative Generation for AAPL and BTC

Demonstrates narrative generation capabilities with real examples
"""

import asyncio

from fiml.core.models import AnalysisDepth, Market
from fiml.mcp.tools import (
    get_narrative,
    search_by_coin,
    search_by_symbol,
)


async def demo_aapl_standard():
    """Demo AAPL with standard depth analysis"""
    print("\n" + "=" * 80)
    print("DEMO: AAPL Stock Analysis with Standard Depth Narrative")
    print("=" * 80)

    response = await search_by_symbol(
        symbol="AAPL",
        market=Market.US,
        depth=AnalysisDepth.STANDARD,
        language="en",
        expertise_level="intermediate",
        include_narrative=True,
    )

    print(f"\nSymbol: {response.symbol}")
    print(f"Name: {response.name}")
    print(f"Exchange: {response.exchange}")
    print(f"Price: ${response.cached.price:.2f}")
    print(f"Change: {response.cached.change:+.2f} ({response.cached.change_percent:+.2f}%)")
    print(f"Source: {response.cached.source}")
    print(f"Confidence: {response.cached.confidence:.2%}")

    if response.narrative:
        print("\n--- NARRATIVE ---")
        print(f"\nSummary:\n{response.narrative.summary}")

        if response.narrative.key_insights:
            print("\nKey Insights:")
            for i, insight in enumerate(response.narrative.key_insights, 1):
                print(f"  {i}. {insight}")

        if response.narrative.risk_factors:
            print("\nRisk Factors:")
            for i, risk in enumerate(response.narrative.risk_factors, 1):
                print(f"  {i}. {risk}")

    print("\nData Lineage:")
    print(f"  Providers: {', '.join(response.data_lineage.providers)}")
    print(f"  Arbitration Score: {response.data_lineage.arbitration_score:.2f}")


async def demo_aapl_deep():
    """Demo AAPL with deep analysis (all sections)"""
    print("\n" + "=" * 80)
    print("DEMO: AAPL Stock Analysis with Deep Depth Narrative")
    print("=" * 80)

    response = await search_by_symbol(
        symbol="AAPL",
        market=Market.US,
        depth=AnalysisDepth.DEEP,
        language="en",
        expertise_level="advanced",
        include_narrative=True,
    )

    print(f"\nSymbol: {response.symbol}")
    print(f"Price: ${response.cached.price:.2f} ({response.cached.change_percent:+.2f}%)")

    if response.narrative:
        print("\n--- COMPREHENSIVE NARRATIVE ---")
        print(f"\nSummary:\n{response.narrative.summary}")

        print("\n--- ALL INSIGHTS ---")
        for i, insight in enumerate(response.narrative.key_insights, 1):
            print(f"{i}. {insight}")

        print("\n--- COMPLETE RISK ANALYSIS ---")
        for i, risk in enumerate(response.narrative.risk_factors, 1):
            print(f"{i}. {risk}")


async def demo_aapl_multilingual():
    """Demo AAPL with multiple languages"""
    print("\n" + "=" * 80)
    print("DEMO: AAPL Stock Analysis in Multiple Languages")
    print("=" * 80)

    languages = [
        ("en", "English"),
        ("es", "Spanish"),
        ("fr", "French"),
    ]

    for lang_code, lang_name in languages:
        print(f"\n--- {lang_name.upper()} ({lang_code}) ---")

        response = await search_by_symbol(
            symbol="AAPL",
            market=Market.US,
            depth=AnalysisDepth.STANDARD,
            language=lang_code,
            expertise_level="intermediate",
            include_narrative=True,
        )

        if response.narrative:
            print(f"Summary: {response.narrative.summary[:200]}...")
            print(f"Insights: {len(response.narrative.key_insights)} insights generated")


async def demo_btc_crypto_narrative():
    """Demo BTC with crypto-specific narrative"""
    print("\n" + "=" * 80)
    print("DEMO: Bitcoin (BTC) Crypto Analysis with Narrative")
    print("=" * 80)

    response = await search_by_coin(
        symbol="BTC",
        exchange="Binance",
        pair="USD",
        depth=AnalysisDepth.STANDARD,
        language="en",
        expertise_level="intermediate",
        include_narrative=True,
    )

    print(f"\nSymbol: {response.symbol}")
    print(f"Name: {response.name}")
    print(f"Pair: {response.pair}")
    print(f"Exchange: {response.exchange}")
    print(f"Price: ${response.cached.price:,.2f}")
    print(f"Change: {response.cached.change:+,.2f} ({response.cached.change_percent:+.2f}%)")

    print("\nCrypto Metrics:")
    if response.crypto_metrics:
        for key, value in response.crypto_metrics.items():
            if isinstance(value, float):
                print(f"  {key}: {value:,.2f}")
            else:
                print(f"  {key}: {value}")

    if response.narrative:
        print("\n--- CRYPTO NARRATIVE ---")
        print(f"\nSummary:\n{response.narrative.summary}")

        print("\nKey Insights (including crypto-specific):")
        for i, insight in enumerate(response.narrative.key_insights, 1):
            print(f"  {i}. {insight}")

        print("\nRisk Factors (crypto warnings):")
        for i, risk in enumerate(response.narrative.risk_factors, 1):
            print(f"  {i}. {risk}")


async def demo_btc_deep_analysis():
    """Demo BTC with deep analysis including blockchain metrics"""
    print("\n" + "=" * 80)
    print("DEMO: Bitcoin Deep Analysis with Blockchain Metrics")
    print("=" * 80)

    response = await search_by_coin(
        symbol="BTC",
        exchange="Coinbase",
        pair="USD",
        depth=AnalysisDepth.DEEP,
        language="en",
        expertise_level="advanced",
        include_narrative=True,
    )

    print("\nBitcoin Deep Analysis")
    print(f"Price: ${response.cached.price:,.2f}")
    print(f"24h Change: {response.cached.change_percent:+.2f}%")
    print(f"Exchange: {response.exchange}")

    if response.narrative:
        print("\n--- DEEP CRYPTO ANALYSIS ---")
        print(f"\nExecutive Summary:\n{response.narrative.summary}")

        print("\n--- Comprehensive Insights ---")
        for insight in response.narrative.key_insights:
            print(f"• {insight}")

        print("\n--- Complete Risk Assessment ---")
        for risk in response.narrative.risk_factors:
            print(f"⚠ {risk}")


async def demo_standalone_narrative():
    """Demo standalone narrative generation with custom data"""
    print("\n" + "=" * 80)
    print("DEMO: Standalone Narrative Generation with Custom Analysis Data")
    print("=" * 80)

    # Custom analysis data for AAPL
    analysis_data = {
        "name": "Apple Inc.",
        "region": "US",
        "sources": ["yahoo_finance", "alpha_vantage"],
        "price_data": {
            "price": 178.50,
            "change": 3.20,
            "change_percent": 1.83,
            "volume": 55000000,
            "high": 179.20,
            "low": 175.80,
        },
        "technical_data": {
            "trend": "bullish",
            "strength": "strong",
            "rsi": 68,
            "macd": "positive",
            "moving_averages": {
                "ma_50": 172.30,
                "ma_200": 165.50,
            },
        },
        "fundamental_data": {
            "market_cap": 2800000000000,
            "pe_ratio": 28.5,
            "eps": 6.26,
            "sector": "Technology",
            "industry": "Consumer Electronics",
        },
        "sentiment_data": {
            "overall": "positive",
            "news_sentiment": 0.72,
            "social_sentiment": 0.65,
        },
        "risk_data": {
            "beta": 1.25,
            "volatility": "moderate",
            "regulatory_risk": "low",
        },
    }

    result = await get_narrative(
        symbol="AAPL",
        asset_type="equity",
        language="en",
        expertise_level="advanced",
        analysis_data=analysis_data,
        focus_areas=["market", "technical", "fundamental", "sentiment", "risk"],
    )

    print(f"\nSymbol: {result['symbol']}")
    print(f"Asset Type: {result['asset_type']}")
    print(f"Language: {result['language']}")
    print(f"Expertise Level: {result['expertise_level']}")
    print(f"Cached: {result.get('cached', False)}")

    if "narrative" in result:
        narrative = result["narrative"]

        print("\n--- FULL NARRATIVE ---")
        print(f"\nWord Count: {narrative['word_count']}")
        print(f"Generation Time: {narrative['generation_time_ms']:.2f}ms")
        print(f"Confidence: {narrative['confidence']:.2%}")

        print(f"\n{narrative['summary']}")

        print("\n--- SECTIONS ---")
        for section in narrative["sections"]:
            print(f"\n{section['title']} ({section['type']})")
            print(f"Confidence: {section['confidence']:.2%}")
            print(section["content"][:200] + "...")

        print("\n--- KEY INSIGHTS ---")
        for insight in narrative["key_insights"]:
            print(f"• {insight}")

        print("\n--- RISK FACTORS ---")
        for risk in narrative["risk_factors"]:
            print(f"⚠ {risk}")


async def demo_narrative_formats():
    """Demo different narrative output formats"""
    print("\n" + "=" * 80)
    print("DEMO: Narrative Output Formats (Text, Markdown)")
    print("=" * 80)

    result = await get_narrative(
        symbol="AAPL",
        asset_type="equity",
        language="en",
        expertise_level="intermediate",
        analysis_data={
            "price_data": {"price": 175.0, "change": 2.0, "change_percent": 1.16}
        },
    )

    if "narrative" in result:
        narrative = result["narrative"]

        print("\n--- PLAIN TEXT FORMAT ---")
        print(narrative.get("full_text", "N/A")[:500] + "...")

        print("\n\n--- MARKDOWN FORMAT ---")
        print(narrative.get("markdown", "N/A")[:500] + "...")


async def demo_cache_efficiency():
    """Demo narrative caching efficiency"""
    print("\n" + "=" * 80)
    print("DEMO: Narrative Caching Efficiency")
    print("=" * 80)

    import time

    # First call - generates narrative
    start = time.time()
    result1 = await get_narrative(
        symbol="AAPL",
        asset_type="equity",
        language="en",
        expertise_level="intermediate",
        analysis_data={"price_data": {"price": 175.0, "change": 1.0, "change_percent": 0.57}},
    )
    time1 = (time.time() - start) * 1000

    print("\nFirst call (generation):")
    print(f"  Time: {time1:.2f}ms")
    print(f"  Cached: {result1.get('cached', False)}")
    if "narrative" in result1:
        print(f"  Generation Time: {result1['narrative']['generation_time_ms']:.2f}ms")

    # Second call - uses cache
    start = time.time()
    result2 = await get_narrative(
        symbol="AAPL",
        asset_type="equity",
        language="en",
        expertise_level="intermediate",
        analysis_data={"price_data": {"price": 175.0, "change": 1.0, "change_percent": 0.57}},
    )
    time2 = (time.time() - start) * 1000

    print("\nSecond call (cached):")
    print(f"  Time: {time2:.2f}ms")
    print(f"  Cached: {result2.get('cached', False)}")
    print(f"  Speedup: {time1 / time2:.2f}x faster")


async def main():
    """Run all demos"""
    print("\n" + "=" * 80)
    print("MCP NARRATIVE GENERATION EXAMPLES")
    print("Demonstrating narrative capabilities for AAPL and BTC")
    print("=" * 80)

    try:
        # AAPL demos
        await demo_aapl_standard()
        await demo_aapl_deep()
        await demo_aapl_multilingual()

        # BTC demos
        await demo_btc_crypto_narrative()
        await demo_btc_deep_analysis()

        # Advanced demos
        await demo_standalone_narrative()
        await demo_narrative_formats()
        await demo_cache_efficiency()

        print("\n" + "=" * 80)
        print("All demos completed successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
