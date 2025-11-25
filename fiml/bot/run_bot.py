"""
FIML Educational Bot Entry Point
Run the Telegram bot with BYOK support
"""

import logging
import os
from pathlib import Path
from typing import Optional

import structlog
from dotenv import load_dotenv

from fiml.bot.adapters.telegram_adapter import TelegramBotAdapter
from fiml.bot.core.key_manager import UserProviderKeyManager
from fiml.bot.core.provider_configurator import FIMLProviderConfigurator

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


def main() -> None:
    """Main entry point"""

    # Get bot token from environment
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not set in environment")
        print("❌ Error: TELEGRAM_BOT_TOKEN environment variable not set")
        print("Set it in .env file or export it:")
        print("export TELEGRAM_BOT_TOKEN='your-bot-token-here'")
        return

    # Get encryption key (or generate)
    encryption_key_str = os.getenv("ENCRYPTION_KEY")
    encryption_key_bytes: Optional[bytes] = None
    if encryption_key_str:
        encryption_key_bytes = encryption_key_str.encode()

    # Setup storage path
    storage_path = os.getenv("KEY_STORAGE_PATH", "./data/keys")
    Path(storage_path).mkdir(parents=True, exist_ok=True)

    logger.info("Starting FIML Educational Bot", storage_path=storage_path)

    # Initialize components
    key_manager = UserProviderKeyManager(
        encryption_key=encryption_key_bytes,
        storage_path=storage_path
    )

    provider_configurator = FIMLProviderConfigurator(key_manager)

    telegram_bot = TelegramBotAdapter(
        token=bot_token,
        key_manager=key_manager,
        provider_configurator=provider_configurator
    )

    # Run the bot
    logger.info("Bot initialized, starting polling...")
    print("🤖 FIML Educational Bot is starting...")
    print("Press Ctrl+C to stop")

    try:
        telegram_bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        print("\n👋 Bot stopped")


if __name__ == "__main__":
    main()
