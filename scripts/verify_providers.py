import asyncio

# Configure logging to stdout
import logging
import time
from datetime import datetime

from fiml.core.config import settings
from fiml.core.models import Asset, AssetType
from fiml.providers import provider_registry

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def verify_providers():
    """Verify all registered providers by fetching real data"""
    print(f"Starting provider verification at {datetime.now()}")
    print(f"Environment: {settings.fiml_env}")

    # Initialize registry
    await provider_registry.initialize()

    providers = provider_registry.providers
    print(f"\nRegistered Providers ({len(providers)}):")
    for name in providers:
        print(f" - {name}")

    print("\n--- Starting Verification ---\n")

    results = {}

    # Test assets
    stock_asset = Asset(symbol="AAPL", asset_type=AssetType.EQUITY)
    crypto_asset = Asset(symbol="BTC", asset_type=AssetType.CRYPTO)

    try:
        for name, provider in providers.items():
            print(f"Testing {name}...")
            start_time = time.time()
            success = False
            error = None
            data = None

            try:
                # Determine which asset to test based on provider capabilities
                # This is a heuristic; ideally we'd check supports_asset first
                if name in ["coingecko", "coinmarketcap", "ccxt_binance"]:
                    test_asset = crypto_asset
                else:
                    test_asset = stock_asset

                # Check support first
                if not await provider.supports_asset(test_asset):
                    if test_asset == stock_asset:
                        test_asset = crypto_asset
                    else:
                        test_asset = stock_asset

                    if not await provider.supports_asset(test_asset):
                        print("  [SKIP] Does not support AAPL or BTC")
                        results[name] = "SKIPPED"
                        continue

                # Fetch price
                response = await provider.fetch_price(test_asset)
                success = True
                data = response.data

            except Exception as e:
                error = str(e)

            duration = (time.time() - start_time) * 1000

            if success:
                print(f"  [PASS] {duration:.2f}ms | Data: {data}")
                results[name] = "PASS"
            else:
                print(f"  [FAIL] {duration:.2f}ms | Error: {error}")
                results[name] = "FAIL"

        print("\n--- Summary ---")
        for name, result in results.items():
            print(f"{name}: {result}")

    finally:
        await provider_registry.shutdown()

if __name__ == "__main__":
    asyncio.run(verify_providers())
