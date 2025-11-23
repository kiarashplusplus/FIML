"""
Example usage of FIML MCP tools
"""

import asyncio

from fiml.core.models import AnalysisDepth, Market
from fiml.mcp.tools import search_by_coin, search_by_symbol


async def example_search_equity():
    """Example: Search for an equity"""
    print("=" * 60)
    print("Example 1: Search for Tesla (TSLA)")
    print("=" * 60)

    result = await search_by_symbol(
        symbol="TSLA", market=Market.US, depth=AnalysisDepth.STANDARD, language="en"
    )

    print(f"\n📊 {result.name} ({result.symbol})")
    print(f"Exchange: {result.exchange}")
    print(f"Price: ${result.cached.price:.2f}")
    print(f"Change: {result.cached.change:+.2f} ({result.cached.change_percent:+.2f}%)")
    print(f"Confidence: {result.cached.confidence:.1%}")
    print(f"\n📋 Task ID: {result.task.id}")
    print(f"Status: {result.task.status}")
    print(f"Type: {result.task.type}")
    print(f"\n📊 Data Sources: {', '.join(result.data_lineage.providers)}")
    print(f"Arbitration Score: {result.data_lineage.arbitration_score:.1f}/100")


async def example_search_crypto():
    """Example: Search for cryptocurrency"""
    print("\n" + "=" * 60)
    print("Example 2: Search for Bitcoin (BTC)")
    print("=" * 60)

    result = await search_by_coin(
        symbol="BTC",
        exchange="binance",
        pair="USDT",
        depth=AnalysisDepth.DEEP,
        language="en",
    )

    print(f"\n💰 {result.name} ({result.pair})")
    print(f"Exchange: {result.exchange}")
    print(f"Price: ${result.cached.price:,.2f}")
    print(f"Change: {result.cached.change:+,.2f} ({result.cached.change_percent:+.2f}%)")
    print(f"Confidence: {result.cached.confidence:.1%}")

    if result.crypto_metrics:
        print("\n📈 Crypto Metrics:")
        print(f"  Dominance: {result.crypto_metrics.get('dominance', 0):.2f}%")
        print(f"  ATH: ${result.crypto_metrics.get('ath', 0):,.2f}")
        print(f"  24h Volume: ${result.crypto_metrics.get('volume24h', 0):,.0f}")

    print(f"\n📋 Task ID: {result.task.id}")
    print(f"Status: {result.task.status}")


async def example_fk_dsl():
    """Example: Execute FK-DSL query"""
    print("\n" + "=" * 60)
    print("Example 3: FK-DSL Query")
    print("=" * 60)

    query = "EVALUATE TSLA: PRICE, VOLATILITY(30d), CORRELATE(BTC, SPY), TECHNICAL(RSI, MACD)"
    print(f"\nQuery: {query}")

    # Note: FK-DSL execution not fully implemented yet
    print("\n⚠️  FK-DSL execution coming soon!")


async def main():
    """Run all examples"""
    print("\n🚀 FIML Example Usage\n")

    await example_search_equity()
    await example_search_crypto()
    await example_fk_dsl()

    print("\n" + "=" * 60)
    print("✅ Examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
