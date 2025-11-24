#!/usr/bin/env python3
"""
Demo script for FIML Educational Bot BYOK functionality
Demonstrates key management without running the full bot

Note: Run with: cd fiml/bot && python ../../examples/bot_demo_standalone.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Direct imports to avoid fiml.__init__.py
from fiml.bot.core.key_manager import UserProviderKeyManager
from fiml.bot.core.provider_configurator import FIMLProviderConfigurator


async def demo_key_management():
    """Demo the key management system"""
    
    print("=" * 60)
    print("FIML Educational Bot - BYOK Demo")
    print("=" * 60)
    print()
    
    # Initialize key manager
    print("1. Initializing UserProviderKeyManager...")
    storage_path = "/tmp/fiml_demo_keys"
    Path(storage_path).mkdir(parents=True, exist_ok=True)
    
    key_manager = UserProviderKeyManager(storage_path=storage_path)
    print(f"   ✓ Initialized with storage at {storage_path}")
    print()
    
    # List supported providers
    print("2. Supported Providers:")
    providers = key_manager.list_supported_providers()
    for provider in providers:
        free_tier = "✓ Free tier" if provider.get("free_tier") else "Paid only"
        print(f"   • {provider['name']}: {free_tier}")
        if provider.get("free_limit"):
            print(f"     Limit: {provider['free_limit']}")
    print()
    
    # Simulate adding a key (without actual API key)
    print("3. Key Format Validation:")
    test_cases = [
        ("alpha_vantage", "ABC123XYZ456789X", "Valid format"),
        ("alpha_vantage", "TOOSHORT", "Too short"),
        ("polygon", "a" * 32, "Valid format"),
        ("finnhub", "a" * 20, "Valid format"),
    ]
    
    for provider, key, description in test_cases:
        valid = key_manager.validate_key_format(provider, key)
        status = "✓" if valid else "✗"
        print(f"   {status} {provider}: {description}")
    print()
    
    # Initialize configurator
    print("4. Initializing FIMLProviderConfigurator...")
    configurator = FIMLProviderConfigurator(key_manager)
    print("   ✓ Configurator ready")
    print()
    
    # Get user config (empty)
    print("5. User Provider Configuration (New User):")
    config = await configurator.get_user_provider_config("demo_user_123")
    print(f"   User ID: {config['user_id']}")
    print(f"   Free Tier: {config['free_tier']}")
    print(f"   Providers: {len(config['providers'])}")
    for provider in config['providers']:
        print(f"     - {provider['name']} (Priority: {provider['priority']})")
    print()
    
    print("=" * 60)
    print("Demo Complete!")
    print("=" * 60)
    print()
    print("To run the actual bot:")
    print("1. Get a Telegram bot token from @BotFather")
    print("2. Set TELEGRAM_BOT_TOKEN in .env")
    print("3. Run: python -m fiml.bot.run_bot")
    print()


if __name__ == "__main__":
    asyncio.run(demo_key_management())
