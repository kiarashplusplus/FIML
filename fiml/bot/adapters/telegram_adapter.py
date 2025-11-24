"""
Component 4: Telegram Bot Adapter
Handles Telegram bot integration with conversation flows for key management
"""

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from fiml.bot.core.key_manager import UserProviderKeyManager
from fiml.bot.core.provider_configurator import FIMLProviderConfigurator

logger = structlog.get_logger(__name__)


# Conversation states
PROVIDER_SELECT, KEY_ENTRY, CONFIRMATION = range(3)


class TelegramBotAdapter:
    """
    Telegram bot adapter with BYOK key management

    Features:
    - Bot command handlers (/start, /addkey, /listkeys, /help, etc.)
    - Multi-step conversation flows for key onboarding
    - Inline keyboards for interactive UI
    - Message formatting with Telegram markdown
    """

    def __init__(
        self,
        token: str,
        key_manager: UserProviderKeyManager,
        provider_configurator: FIMLProviderConfigurator
    ):
        """
        Initialize Telegram bot adapter

        Args:
            token: Telegram bot token
            key_manager: User provider key manager
            provider_configurator: FIML provider configurator
        """
        self.token = token
        self.key_manager = key_manager
        self.provider_configurator = provider_configurator

        # Build application
        self.application = Application.builder().token(token).build()

        # Setup handlers
        self._setup_handlers()

        logger.info("TelegramBotAdapter initialized")

    def _setup_handlers(self):
        """Setup all command and conversation handlers"""

        # Basic commands
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("listkeys", self.cmd_list_keys))

        # Add key conversation flow
        add_key_conv = ConversationHandler(
            entry_points=[CommandHandler("addkey", self.cmd_add_key)],
            states={
                PROVIDER_SELECT: [
                    CallbackQueryHandler(self.select_provider, pattern="^provider:")
                ],
                KEY_ENTRY: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_key)
                ],
                CONFIRMATION: [
                    CallbackQueryHandler(self.confirm_key, pattern="^confirm:")
                ],
            },
            fallbacks=[CommandHandler("cancel", self.cmd_cancel)],
        )
        self.application.add_handler(add_key_conv)

        # Remove key command
        self.application.add_handler(CommandHandler("removekey", self.cmd_remove_key))

        # Test key command
        self.application.add_handler(CommandHandler("testkey", self.cmd_test_key))

        # Status command
        self.application.add_handler(CommandHandler("status", self.cmd_status))

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user

        welcome_text = f"""
👋 Welcome to FIML Educational Bot, {user.first_name}!

I'll help you learn trading and investing with **real market data**.

🔑 **Get Started:**
First, let's set up your data access:

• **Free Tier**: Use Yahoo Finance (no API key needed)
• **Pro Tier**: Add your own API keys for better data

Choose your path:
/addkey - Add API keys for premium data
/help - See all available commands

💡 New to this? Start with the free tier!
"""

        await update.message.reply_text(welcome_text, parse_mode="Markdown")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
📚 **FIML Educational Bot Commands**

**Key Management:**
/addkey - Add a new API key
/listkeys - View your connected providers
/removekey - Remove an API key
/testkey - Test if your keys are working
/status - View your provider status and usage

**Learning:**
/lesson - Start or continue a lesson (coming soon)
/quiz - Practice quiz (coming soon)
/mentor - Talk to AI mentor (coming soon)

**Market Data:**
/market <symbol> - Get market data (coming soon)

**Help:**
/help - Show this message
/cancel - Cancel current operation

💡 Tip: Start by adding your API keys with /addkey!
"""

        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def cmd_add_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start add key conversation"""
        # Get supported providers
        providers = self.key_manager.list_supported_providers()

        # Create inline keyboard
        keyboard = []
        for provider in providers:
            provider_id = provider["id"]
            provider_name = provider["name"]
            free_tier = "✓ Free tier" if provider.get("free_tier") else "Paid only"

            keyboard.append([
                InlineKeyboardButton(
                    f"{provider_name} ({free_tier})",
                    callback_data=f"provider:{provider_id}"
                )
            ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        text = """
🔑 **Add API Key**

Choose which data provider you want to add:

ℹ️ Providers with free tiers let you get started without costs.
"""

        await update.message.reply_text(
            text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

        return PROVIDER_SELECT

    async def select_provider(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle provider selection"""
        query = update.callback_query
        await query.answer()

        # Extract provider from callback data
        provider_id = query.data.split(":")[1]
        context.user_data["selected_provider"] = provider_id

        # Get provider info
        provider_info = self.key_manager.get_provider_info(provider_id)

        if not provider_info:
            await query.edit_message_text("Provider not found. Please try again with /addkey")
            return ConversationHandler.END

        # Provide instructions
        instructions = f"""
📝 **{provider_info['name']} API Key**

**Get your API key:**
🔗 {provider_info['signup_url']}

"""

        if provider_info.get("free_tier"):
            instructions += f"✅ **Free tier available:** {provider_info['free_limit']}\n\n"
        else:
            instructions += f"💳 **Pricing:** {provider_info.get('paid_tiers', 'Check website')}\n\n"

        instructions += """
Once you have your API key, paste it here.

/cancel to abort
"""

        await query.edit_message_text(instructions, parse_mode="Markdown")

        return KEY_ENTRY

    async def receive_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive and validate API key"""
        str(update.effective_user.id)
        provider_id = context.user_data.get("selected_provider")
        api_key = update.message.text.strip()

        # Validate format
        if not self.key_manager.validate_key_format(provider_id, api_key):
            await update.message.reply_text(
                "❌ Invalid key format. Please check and try again.\n\n"
                f"Expected format for {provider_id}: Check the provider's documentation."
            )
            return KEY_ENTRY

        # Test the key
        await update.message.reply_text("🔄 Testing your API key...")

        test_result = await self.key_manager.test_provider_key(provider_id, api_key)

        if not test_result["valid"]:
            await update.message.reply_text(
                f"❌ Key test failed: {test_result['message']}\n\n"
                "Please check your key and try again, or /cancel to abort."
            )
            return KEY_ENTRY

        # Store in context for confirmation
        context.user_data["api_key"] = api_key
        context.user_data["test_result"] = test_result

        # Ask for confirmation
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, save it", callback_data="confirm:yes"),
                InlineKeyboardButton("❌ Cancel", callback_data="confirm:no"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        confirm_text = f"""
✅ **Key validated successfully!**

**Provider:** {provider_id}
**Tier:** {test_result['tier']}
**Message:** {test_result['message']}

Save this key?
"""

        await update.message.reply_text(
            confirm_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

        return CONFIRMATION

    async def confirm_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirm and store API key"""
        query = update.callback_query
        await query.answer()

        confirmation = query.data.split(":")[1]

        if confirmation == "no":
            await query.edit_message_text("❌ Key addition cancelled.")
            return ConversationHandler.END

        # Store the key
        user_id = str(update.effective_user.id)
        provider_id = context.user_data.get("selected_provider")
        api_key = context.user_data.get("api_key")
        test_result = context.user_data.get("test_result", {})

        metadata = {
            "tier": test_result.get("tier", "unknown"),
            "message": test_result.get("message", ""),
        }

        success = await self.key_manager.store_user_key(
            user_id, provider_id, api_key, metadata
        )

        if success:
            success_text = f"""
🎉 **API Key Saved!**

Your {provider_id} key is now connected.

**What's next:**
• /listkeys - View all your keys
• /status - Check usage and limits
• /lesson - Start learning (coming soon)

💡 You can add more providers with /addkey
"""
            await query.edit_message_text(success_text, parse_mode="Markdown")
        else:
            await query.edit_message_text(
                "❌ Failed to save key. Please try again with /addkey"
            )

        # Clear context
        context.user_data.clear()

        return ConversationHandler.END

    async def cmd_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel current operation"""
        context.user_data.clear()
        await update.message.reply_text("❌ Operation cancelled.")
        return ConversationHandler.END

    async def cmd_list_keys(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List user's connected providers"""
        user_id = str(update.effective_user.id)

        providers = await self.key_manager.list_user_providers(user_id)

        if not providers:
            text = """
🔑 **Your API Keys**

You don't have any API keys connected yet.

Add one with /addkey to unlock premium data providers!

💡 Or use the free tier (Yahoo Finance) without any keys.
"""
        else:
            text = "🔑 **Your Connected Providers**\n\n"

            for provider in providers:
                name = provider["name"]
                added = provider.get("added_at", "Unknown")
                tier = provider.get("metadata", {}).get("tier", "unknown")

                text += f"✅ **{name}**\n"
                text += f"   Tier: {tier}\n"
                text += f"   Added: {added[:10]}\n\n"  # Just date

            text += "\n💡 Commands:\n"
            text += "/addkey - Add another provider\n"
            text += "/removekey - Remove a provider\n"
            text += "/status - Check usage"

        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_remove_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove a provider key"""
        user_id = str(update.effective_user.id)

        providers = await self.key_manager.list_user_providers(user_id)

        if not providers:
            await update.message.reply_text("You don't have any keys to remove.")
            return

        # Create inline keyboard
        keyboard = []
        for provider in providers:
            provider_id = provider["provider"]
            provider_name = provider["name"]

            keyboard.append([
                InlineKeyboardButton(
                    f"Remove {provider_name}",
                    callback_data=f"remove:{provider_id}"
                )
            ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Select provider to remove:",
            reply_markup=reply_markup
        )

    async def cmd_test_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Test all user's keys"""
        user_id = str(update.effective_user.id)

        keys = await self.key_manager.get_user_keys(user_id)

        if not keys:
            await update.message.reply_text("You don't have any keys to test.")
            return

        await update.message.reply_text("🔄 Testing your API keys...")

        results = []
        for provider, api_key in keys.items():
            test_result = await self.key_manager.test_provider_key(provider, api_key)
            results.append((provider, test_result))

        # Format results
        text = "🔍 **Key Test Results**\n\n"

        for provider, result in results:
            status = "✅" if result["valid"] else "❌"
            text += f"{status} **{provider}**: {result['message']}\n"

        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show provider status and usage"""
        user_id = str(update.effective_user.id)

        status_list = await self.provider_configurator.get_provider_status(user_id)

        if not status_list:
            text = """
📊 **Provider Status**

No providers connected yet.

/addkey to get started!
"""
        else:
            text = "📊 **Provider Status**\n\n"

            for status in status_list:
                name = status["name"]
                usage = status["usage_today"]
                tier = status["tier"]

                text += f"**{name}**\n"
                text += f"   Tier: {tier}\n"
                text += f"   Usage today: {usage} requests\n"
                text += f"   Status: {status['status']}\n\n"

        await update.message.reply_text(text, parse_mode="Markdown")

    async def start(self):
        """Start the bot"""
        logger.info("Starting Telegram bot...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        logger.info("Telegram bot started")

    async def stop(self):
        """Stop the bot"""
        logger.info("Stopping Telegram bot...")
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()
        logger.info("Telegram bot stopped")

    def run(self):
        """Run the bot (blocking)"""
        self.application.run_polling()
