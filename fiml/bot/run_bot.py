"""
FIML Educational Bot Entry Point
Run the Telegram bot with BYOK support
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

import structlog
from dotenv import load_dotenv

from fiml.bot.adapters.telegram_adapter import TelegramBotAdapter
from fiml.bot.core.key_manager import UserProviderKeyManager
from fiml.bot.core.provider_configurator import FIMLProviderConfigurator
from fiml.bot.education.gamification import GamificationEngine
from fiml.sessions.store import SessionStore

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

    # Initialize session store for persistence
    session_store = SessionStore()

    # Run async initialization and bot
    asyncio.run(run_async(bot_token, encryption_key_bytes, storage_path, session_store))


async def run_async(
    bot_token: str,
    encryption_key: Optional[bytes],
    storage_path: str,
    session_store: SessionStore
) -> None:
    """Async runner to handle SessionStore lifecycle"""

    # Try to initialize session store (Redis + PostgreSQL)
    session_store_enabled = False
    try:
        await session_store.initialize()
        session_store_enabled = True
        logger.info("SessionStore initialized (Redis + PostgreSQL persistence)")
        print("✅ Redis + PostgreSQL session persistence enabled")
    except Exception as e:
        logger.warning(f"SessionStore unavailable, running in standalone mode: {e}")
        print("⚠️  Redis/PostgreSQL unavailable - running with in-memory progress (won't persist)")
        session_store = None  # Gamification will use in-memory dict

    try:
        # Initialize components
        key_manager = UserProviderKeyManager(
            encryption_key=encryption_key,
            storage_path=storage_path
        )

        provider_configurator = FIMLProviderConfigurator(key_manager)

        # Initialize gamification (with or without session store)
        gamification = GamificationEngine(session_store=session_store)

        telegram_bot = TelegramBotAdapter(
            token=bot_token,
            key_manager=key_manager,
            provider_configurator=provider_configurator,
            gamification=gamification
        )

        # Run the bot
        mode = "persistent" if session_store_enabled else "in-memory"
        logger.info(f"Bot initialized ({mode} mode), starting polling...")
        print(f"🤖 FIML Educational Bot is starting ({mode} mode)...")
        print("Press Ctrl+C to stop")

        # Use run_polling() which works in existing async context
        await telegram_bot.application.initialize()
        await telegram_bot.application.start()
        await telegram_bot.application.updater.start_polling()

        # Keep running until interrupted
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        print("\n👋 Bot stopped")
    finally:
        # Cleanup bot
        try:
            await telegram_bot.application.updater.stop()
            await telegram_bot.application.stop()
            await telegram_bot.application.shutdown()
        except:
            pass

        # Cleanup session store if it was initialized
        if session_store_enabled and session_store:
            await session_store.shutdown()
            logger.info("SessionStore shutdown complete")


if __name__ == "__main__":
    main()
