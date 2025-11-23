"""
Agent Workflows Demo

Demonstrates the use of high-level agent workflows for comprehensive financial analysis.
"""

import asyncio

from fiml.agents.workflows import (
    crypto_sentiment_analysis,
    deep_equity_analysis,
)
from fiml.core.models import Market


async def demo_deep_equity_analysis():
    """
    Demo: Deep Equity Analysis Workflow

    Performs comprehensive multi-dimensional analysis combining:
    - Quick price snapshot
    - Fundamental analysis (P/E, ROE, valuation)
    - Technical analysis (RSI, MACD, trends)
    - Sentiment analysis (news, social)
    - Risk assessment (volatility, correlations)
    - LLM-generated narrative
    - Actionable recommendations
    """
    print("=" * 80)
    print("🚀 DEEP EQUITY ANALYSIS WORKFLOW")
    print("=" * 80)
    print()

    # Example 1: Analyze Tesla
    print("📊 Analyzing TSLA (Tesla)...")
    print()

    result = await deep_equity_analysis(
        symbol="TSLA",
        market=Market.US,
        include_narrative=True,
        include_recommendation=True,
    )

    # Display results
    print(f"Status: {result.status.value}")
    print(f"Execution Time: {result.execution_time_ms:.2f}ms")
    print(f"Steps Completed: {result.steps_completed}/{result.steps_total}")
    print()

    # Price Snapshot
    if result.snapshot:
        print("💰 PRICE SNAPSHOT")
        print("-" * 80)
        print(f"  Price: ${result.snapshot.get('price', 0):.2f}")
        print(f"  Change: {result.snapshot.get('change_percent', 0):+.2f}%")
        print(f"  Volume: {result.snapshot.get('volume', 0):,.0f}")
        print(f"  Market Cap: ${result.snapshot.get('market_cap', 0):,.0f}")
        print(f"  Data Provider: {result.snapshot.get('provider', 'N/A')}")
        print()

    # Fundamentals
    if result.fundamentals and not result.fundamentals.get("error"):
        print("📈 FUNDAMENTALS")
        print("-" * 80)
        metrics = result.fundamentals.get("metrics", {})
        print(f"  P/E Ratio: {metrics.get('pe_ratio', 'N/A')}")
        print(f"  EPS: ${metrics.get('eps', 'N/A')}")
        print(f"  ROE: {metrics.get('roe', 'N/A')}")
        print(f"  ROA: {metrics.get('roa', 'N/A')}")
        print(f"  Debt/Equity: {metrics.get('debt_to_equity', 'N/A')}")

        valuation = result.fundamentals.get("valuation", {})
        if valuation:
            print(f"  Valuation: {valuation.get('assessment', 'N/A')}")
            print(f"  Confidence: {valuation.get('confidence', 0):.1%}")
        print()

    # Technical Analysis
    if result.technicals and not result.technicals.get("error"):
        print("📉 TECHNICAL ANALYSIS")
        print("-" * 80)
        indicators = result.technicals.get("indicators", {})
        print(f"  RSI: {indicators.get('rsi', 'N/A')}")
        print(f"  MACD: {indicators.get('macd', 'N/A')}")

        trend = result.technicals.get("trend", {})
        if trend:
            print(f"  Trend: {trend.get('direction', 'N/A')}")
            print(f"  Strength: {trend.get('strength', 'N/A')}")

        levels = result.technicals.get("levels", {})
        if levels:
            print(f"  Support: ${levels.get('support', 'N/A')}")
            print(f"  Resistance: ${levels.get('resistance', 'N/A')}")
        print()

    # Sentiment
    if result.sentiment and not result.sentiment.get("error"):
        print("💭 SENTIMENT ANALYSIS")
        print("-" * 80)
        sent_data = result.sentiment.get("sentiment", {})
        print(f"  Overall Score: {sent_data.get('score', 'N/A')}")
        print(f"  News Sentiment: {sent_data.get('news_sentiment', 'N/A')}")
        print(f"  Social Sentiment: {sent_data.get('social_sentiment', 'N/A')}")
        print()

    # Risk Assessment
    if result.risk and not result.risk.get("error"):
        print("⚠️  RISK ASSESSMENT")
        print("-" * 80)
        risk_data = result.risk.get("risk", {})
        print(f"  Risk Level: {risk_data.get('level', 'N/A')}")
        print(f"  Volatility: {risk_data.get('volatility', 'N/A')}")
        print(f"  Beta: {risk_data.get('beta', 'N/A')}")
        print(f"  Max Drawdown: {risk_data.get('max_drawdown', 'N/A')}")
        print()

    # LLM Narrative
    if result.narrative:
        print("📝 AI-GENERATED NARRATIVE")
        print("-" * 80)
        print(result.narrative)
        print()

    # Recommendation
    if result.recommendation:
        print("💡 RECOMMENDATION")
        print("-" * 80)
        rec = result.recommendation
        action = rec.get("action", "HOLD")
        confidence = rec.get("confidence", "MEDIUM")
        score = rec.get("overall_score", 50)

        # Color-code the action
        action_emoji = {
            "BUY": "🟢",
            "HOLD": "🟡",
            "SELL": "🔴",
        }
        print(f"  {action_emoji.get(action, '⚪')} Action: {action}")
        print(f"  Confidence: {confidence}")
        print(f"  Overall Score: {score:.2f}/100")
        print()

        # Component scores
        component_scores = rec.get("component_scores", {})
        if component_scores:
            print("  Component Scores:")
            for component, score in component_scores.items():
                print(f"    - {component}: {score:.2f}")
        print()

        reasoning = rec.get("reasoning", "")
        if reasoning:
            print(f"  Reasoning: {reasoning}")
        print()

    # Quality Metrics
    print("📊 DATA QUALITY & CONFIDENCE")
    print("-" * 80)
    print(f"  Data Quality Score: {result.data_quality_score:.1f}%")
    print(f"  Confidence Score: {result.confidence_score:.1%}")
    print()

    if result.warnings:
        print("⚠️  WARNINGS")
        print("-" * 80)
        for warning in result.warnings:
            print(f"  - {warning}")
        print()

    print("=" * 80)
    print()


async def demo_crypto_sentiment_analysis():
    """
    Demo: Crypto Sentiment Analysis Workflow

    Specialized cryptocurrency analysis combining:
    - Real-time price data
    - Technical indicators (RSI, MACD, volume)
    - Sentiment from news and social media
    - Correlation with BTC/ETH
    - LLM market narrative
    - Trading signals
    """
    print("=" * 80)
    print("🪙 CRYPTO SENTIMENT ANALYSIS WORKFLOW")
    print("=" * 80)
    print()

    # Example: Analyze Ethereum
    print("📊 Analyzing ETH (Ethereum) on Binance...")
    print()

    result = await crypto_sentiment_analysis(
        symbol="ETH",
        exchange="binance",
        pair="USDT",
        include_narrative=True,
    )

    # Display results
    print(f"Status: {result.status.value}")
    print(f"Execution Time: {result.execution_time_ms:.2f}ms")
    print(f"Steps Completed: {result.steps_completed}/{result.steps_total}")
    print()

    # Price Data
    if result.price_data and not result.price_data.get("error"):
        print("💰 PRICE DATA")
        print("-" * 80)
        print(f"  Price: ${result.price_data.get('price', 0):,.2f}")
        print(f"  Change: {result.price_data.get('change', 0):+,.2f}")
        print(f"  Change %: {result.price_data.get('change_percent', 0):+.2f}%")
        print(f"  Volume: {result.price_data.get('volume', 0):,.2f}")
        print(f"  24h High: ${result.price_data.get('high_24h', 0):,.2f}")
        print(f"  24h Low: ${result.price_data.get('low_24h', 0):,.2f}")
        print()

    # Sentiment
    if result.sentiment and not result.sentiment.get("error"):
        print("💭 SENTIMENT ANALYSIS")
        print("-" * 80)
        sent_data = result.sentiment.get("sentiment", {})
        print(f"  Overall Score: {sent_data.get('score', 'N/A')}")
        print(f"  Trend: {sent_data.get('trend', 'N/A')}")

        news_data = result.sentiment.get("news", {})
        if news_data:
            print(f"  News Count: {news_data.get('count', 0)}")
            print(f"  News Sentiment: {news_data.get('sentiment', 'N/A')}")
        print()

    # Technical Analysis
    if result.technicals and not result.technicals.get("error"):
        print("📉 TECHNICAL INDICATORS")
        print("-" * 80)
        indicators = result.technicals.get("indicators", {})
        print(f"  RSI (14): {indicators.get('rsi', 'N/A')}")
        print(f"  MACD: {indicators.get('macd', 'N/A')}")
        print(f"  Signal Line: {indicators.get('signal', 'N/A')}")

        volume = result.technicals.get("volume", {})
        if volume:
            print(f"  Volume Trend: {volume.get('trend', 'N/A')}")
        print()

    # Correlations
    if result.correlations and not result.correlations.get("error"):
        print("🔗 CORRELATIONS")
        print("-" * 80)
        btc_corr = result.correlations.get("btc_correlation", "N/A")
        eth_corr = result.correlations.get("eth_correlation", "N/A")
        print(f"  BTC Correlation: {btc_corr}")
        print(f"  ETH Correlation: {eth_corr}")
        print()

    # LLM Narrative
    if result.narrative:
        print("📝 MARKET NARRATIVE")
        print("-" * 80)
        print(result.narrative)
        print()

    # Trading Signals
    if result.signals:
        print("🎯 TRADING SIGNALS")
        print("-" * 80)
        signal = result.signals.get("signal", "NEUTRAL")
        strength = result.signals.get("strength", 0)

        signal_emoji = {
            "BUY": "🟢",
            "SELL": "🔴",
            "NEUTRAL": "🟡",
        }
        print(f"  {signal_emoji.get(signal, '⚪')} Signal: {signal}")
        print(f"  Strength: {strength}/100")
        print()

        indicators = result.signals.get("indicators", [])
        if indicators:
            print("  Key Indicators:")
            for indicator in indicators:
                print(f"    - {indicator}")
        print()

    # Confidence
    print("📊 CONFIDENCE METRICS")
    print("-" * 80)
    print(f"  Overall Confidence: {result.confidence_score:.1%}")
    print()

    if result.warnings:
        print("⚠️  WARNINGS")
        print("-" * 80)
        for warning in result.warnings:
            print(f"  - {warning}")
        print()

    print("=" * 80)
    print()


async def demo_workflow_comparison():
    """
    Demo: Compare multiple assets using workflows
    """
    print("=" * 80)
    print("🔍 MULTI-ASSET COMPARISON")
    print("=" * 80)
    print()

    # Analyze multiple tech stocks
    symbols = ["AAPL", "MSFT", "GOOGL"]

    print(f"Analyzing {len(symbols)} tech stocks in parallel...")
    print()

    # Run analyses in parallel
    results = await asyncio.gather(
        *[
            deep_equity_analysis(symbol, market=Market.US, include_narrative=False)
            for symbol in symbols
        ]
    )

    # Create comparison table
    print("COMPARISON TABLE")
    print("-" * 80)
    print(f"{'Symbol':<10} {'Price':<12} {'P/E':<10} {'Score':<10} {'Action':<10}")
    print("-" * 80)

    for symbol, result in zip(symbols, results, strict=False):
        price = result.snapshot.get("price", 0) if result.snapshot else 0
        pe = result.fundamentals.get("metrics", {}).get("pe_ratio", "N/A") if result.fundamentals else "N/A"
        score = result.recommendation.get("overall_score", 0) if result.recommendation else 0
        action = result.recommendation.get("action", "N/A") if result.recommendation else "N/A"

        print(f"{symbol:<10} ${price:<11.2f} {str(pe):<10} {score:<10.1f} {action:<10}")

    print("-" * 80)
    print()


async def demo_workflow_with_error_handling():
    """
    Demo: Workflow with error handling and partial results
    """
    print("=" * 80)
    print("🛡️  ERROR HANDLING & RESILIENCE")
    print("=" * 80)
    print()

    # Try to analyze an invalid symbol
    print("Attempting to analyze invalid symbol 'INVALID'...")
    print()

    result = await deep_equity_analysis(
        symbol="INVALID",
        market=Market.US,
        include_narrative=True,
    )

    print(f"Status: {result.status.value}")
    print(f"Steps Completed: {result.steps_completed}/{result.steps_total}")

    if result.error:
        print(f"Error: {result.error}")

    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  - {warning}")

    # Even with errors, check what data was collected
    print("\nPartial Data Collection:")
    print(f"  Snapshot: {'✓' if result.snapshot else '✗'}")
    print(f"  Fundamentals: {'✓' if result.fundamentals else '✗'}")
    print(f"  Technicals: {'✓' if result.technicals else '✗'}")
    print(f"  Sentiment: {'✓' if result.sentiment else '✗'}")
    print(f"  Risk: {'✓' if result.risk else '✗'}")
    print()

    print("=" * 80)
    print()


async def main():
    """Run all workflow demos"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "FIML AGENT WORKFLOWS DEMO" + " " * 33 + "║")
    print("╚" + "═" * 78 + "╝")
    print()

    # Run demos
    await demo_deep_equity_analysis()

    await demo_crypto_sentiment_analysis()

    await demo_workflow_comparison()

    await demo_workflow_with_error_handling()

    print("=" * 80)
    print("✅ All workflow demos completed!")
    print("=" * 80)
    print()


if __name__ == "__main__":
    asyncio.run(main())
