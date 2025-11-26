#!/usr/bin/env python3
"""
Test script to verify no Binance requests are made when API key is not configured
"""
import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fiml.core.config import settings
from fiml.core.logging import get_logger
from fiml.providers.registry import provider_registry

logger = get_logger(__name__)


async def main():
    """Test that Binance provider is not registered when API key is empty"""

    print("=" * 60)
    print("Testing Binance Provider Registration")
    print("=" * 60)

    # Check .env configuration
    print("\n1. Checking .env configuration:")
    print(f"   BINANCE_API_KEY: '{settings.binance_api_key}'")
    print(f"   Is empty: {not settings.binance_api_key}")

    # Initialize provider registry
    print("\n2. Initializing provider registry...")
    await provider_registry.initialize()

    # Check registered providers
    print(f"\n3. Registered providers ({len(provider_registry.providers)}):")
    for name in sorted(provider_registry.providers.keys()):
        print(f"   - {name}")

    # Check if CCXT Binance is registered
    ccxt_providers = [name for name in provider_registry.providers if name.startswith("ccxt_")]
    print(f"\n4. CCXT providers registered: {len(ccxt_providers)}")
    for name in ccxt_providers:
        print(f"   - {name}")

    # Verify Binance is NOT registered
    binance_registered = "ccxt_binance" in provider_registry.providers
    print("\n5. Result:")
    print(f"   ccxt_binance registered: {binance_registered}")

    if binance_registered:
        print("   ❌ FAIL: Binance provider should NOT be registered without API key")
        return False
    else:
        print("   ✅ PASS: Binance provider correctly skipped (no API key)")
        return True


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
