"""
Component 4: Telegram Bot Adapter
Handles Telegram bot integration with conversation flows for key management
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import structlog
import yaml
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
from fiml.bot.education.ai_mentor import AIMentorService, MentorPersona
from fiml.bot.education.compliance_filter import EducationalComplianceFilter
from fiml.bot.education.gamification import GamificationEngine
from fiml.bot.education.lesson_engine import LessonContentEngine
from fiml.bot.education.quiz_system import QuizSystem
from fiml.mcp.tools import execute_fk_dsl

logger = structlog.get_logger(__name__)


# Conversation states
PROVIDER_SELECT: int
KEY_ENTRY: int
CONFIRMATION: int
PROVIDER_SELECT, KEY_ENTRY, CONFIRMATION = range(3)

# FK-DSL Query Templates
DSL_TEMPLATES = {
    "analyze_stock": {
        "display": "📊 Analyze Stock",
        "query": "EVALUATE AAPL: PRICE, VOLUME, VOLATILITY(30d)",
        "description": "Get comprehensive analysis of a stock with price, volume, and 30-day volatility",
        "example": "Try with: TSLA, MSFT, or NVDA",
    },
    "compare_tech": {
        "display": "⚖️ Compare Tech Giants",
        "query": "COMPARE AAPL, MSFT, GOOGL BY PE, MARKETCAP, VOLUME",
        "description": "Side-by-side comparison of major tech stocks by key metrics",
        "example": "Compare any 2-5 stocks",
    },
    "correlate_crypto": {
        "display": "🔗 Crypto Correlation",
        "query": "CORRELATE BTC WITH ETH, SPY WINDOW 30d",
        "description": "Analyze 30-day correlation between Bitcoin and other assets",
        "example": "Useful for portfolio diversification",
    },
    "scan_stocks": {
        "display": "🔍 Stock Scanner",
        "query": "SCAN US_TECH WHERE PE < 30 AND VOLUME > 1000000",
        "description": "Find tech stocks with P/E ratio under 30 and high volume",
        "example": "Customize the criteria to find opportunities",
    },
    "custom": {
        "display": "✏️ Custom Query",
        "query": "",
        "description": "Write your own FK-DSL query for advanced analysis",
        "example": "Use EVALUATE, COMPARE, CORRELATE, or SCAN",
    },
}


class TelegramBotAdapter:
    """
    Telegram bot adapter with BYOK key management

    Features:
    - Bot command handlers (/start, /addkey, /listkeys, /help, etc.)
    - Multi-step conversation flows for key onboarding
    - Inline keyboards for interactive UI
    - Message formatting with Telegram markdown
    - Educational features: lessons, quizzes, AI mentors
    - Gamification: XP, levels, streaks
    """

    def __init__(
        self,
        token: str,
        key_manager: UserProviderKeyManager,
        provider_configurator: FIMLProviderConfigurator,
        lesson_engine: Optional[LessonContentEngine] = None,
        quiz_system: Optional[QuizSystem] = None,
        mentor_service: Optional[AIMentorService] = None,
        gamification: Optional[GamificationEngine] = None,
        compliance_filter: Optional[EducationalComplianceFilter] = None,
    ):
        """
        Initialize Telegram bot adapter

        Args:
            token: Telegram bot token
            key_manager: User provider key manager
            provider_configurator: FIML provider configurator
            lesson_engine: Lesson content engine (optional)
            quiz_system: Quiz system (optional)
            mentor_service: AI mentor service (optional)
            gamification: Gamification engine (optional)
            compliance_filter: Compliance filter (optional)
        """
        self.token = token
        self.key_manager = key_manager
        self.provider_configurator = provider_configurator

        # Educational components (create if not provided)
        self.lesson_engine = lesson_engine or LessonContentEngine()
        self.quiz_system = quiz_system or QuizSystem()
        self.mentor_service = mentor_service or AIMentorService()
        self.gamification = gamification or GamificationEngine()
        self.compliance_filter = compliance_filter or EducationalComplianceFilter()

        # Build application
        self.application = Application.builder().token(token).build()

        # Setup handlers
        self._setup_handlers()

        logger.info("TelegramBotAdapter initialized")

    def _setup_handlers(self) -> None:
        """Setup all command and conversation handlers"""

        # Basic commands
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("listkeys", self.cmd_list_keys))

        # Add key conversation flow
        add_key_conv = ConversationHandler(
            entry_points=[CommandHandler("addkey", self.cmd_add_key)],
            states={
                PROVIDER_SELECT: [CallbackQueryHandler(self.select_provider, pattern="^provider:")],
                KEY_ENTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_key)],
                CONFIRMATION: [CallbackQueryHandler(self.confirm_key, pattern="^confirm:")],
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

        # Educational commands
        self.application.add_handler(CommandHandler("lesson", self.cmd_lesson))
        self.application.add_handler(CommandHandler("quiz", self.cmd_quiz))
        self.application.add_handler(CommandHandler("mentor", self.cmd_mentor))
        self.application.add_handler(CommandHandler("progress", self.cmd_progress))
        self.application.add_handler(CommandHandler("fkdsl", self.cmd_fkdsl))

        # Mentor persona selection
        self.application.add_handler(CallbackQueryHandler(self.select_mentor, pattern="^mentor:"))

        # Lesson selection
        self.application.add_handler(CallbackQueryHandler(self.select_lesson, pattern="^lesson:"))

        # Quiz answer handling
        self.application.add_handler(
            CallbackQueryHandler(self.handle_quiz_answer, pattern="^quiz_answer:")
        )

        # DSL template selection
        self.application.add_handler(
            CallbackQueryHandler(self.handle_dsl_template, pattern="^dsl_template:")
        )

        # Remove key callback
        self.application.add_handler(
            CallbackQueryHandler(self.handle_remove_key, pattern="^remove:")
        )

        # General message handler (must be last)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
        user = update.effective_user

        welcome_text = f"""
👋 Welcome to Trading Educational Bot, {user.first_name}!

I'll help you learn trading and investing with **real market data**.

🔑 **Get Started:**
First, let's set up your data access:

• **Free Tier**: Use Yahoo Finance (no API key needed)
• **Pro Tier**: Add your own API keys for better data

Choose your path:
/addkey - Add API keys for premium data
/lesson - Browse and start lessons
/help - See all available commands

💡 New to this? Start learning with the free tier by clicking on /lesson !
"""

        await update.message.reply_text(welcome_text, parse_mode="Markdown")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
/lesson - Browse and start lessons
/quiz - Take a practice quiz
/mentor - Talk to AI mentor
/progress - View your learning progress

**Advanced Analysis:**
/fkdsl - Run Financial Knowledge DSL queries

**Help:**
/help - Show this message
/cancel - Cancel current operation

💡 Tip: Start by adding your API keys with /addkey!
"""

        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def cmd_add_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start add key conversation"""
        # Get supported providers
        providers = self.key_manager.list_supported_providers()

        # Create inline keyboard
        keyboard = []
        for provider in providers:
            provider_id = provider["id"]
            provider_name = provider["name"]
            free_tier = "✓ Free tier" if provider.get("free_tier") else "Paid only"

            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"{provider_name} ({free_tier})", callback_data=f"provider:{provider_id}"
                    )
                ]
            )

        reply_markup = InlineKeyboardMarkup(keyboard)

        text = """
🔑 **Add API Key**

Choose which data provider you want to add:

ℹ️ Providers with free tiers let you get started without costs.
"""

        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

        return PROVIDER_SELECT

    async def select_provider(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
            return int(ConversationHandler.END)

        # Provide instructions
        instructions = f"""
📝 **{provider_info['name']} API Key**

**Get your API key:**
🔗 {provider_info['signup_url']}

"""

        if provider_info.get("free_tier"):
            instructions += f"✅ **Free tier available:** {provider_info['free_limit']}\n\n"
        else:
            instructions += (
                f"💳 **Pricing:** {provider_info.get('paid_tiers', 'Check website')}\n\n"
            )

        instructions += """
Once you have your API key, paste it here.

/cancel to abort
"""

        await query.edit_message_text(instructions, parse_mode="Markdown")

        return KEY_ENTRY

    async def receive_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
            confirm_text, reply_markup=reply_markup, parse_mode="Markdown"
        )

        return CONFIRMATION

    async def confirm_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Confirm and store API key"""
        query = update.callback_query
        await query.answer()

        confirmation = query.data.split(":")[1]

        if confirmation == "no":
            await query.edit_message_text("❌ Key addition cancelled.")
            return int(ConversationHandler.END)

        # Store the key
        user_id = str(update.effective_user.id)
        provider_id = context.user_data.get("selected_provider")
        api_key = context.user_data.get("api_key")
        test_result = context.user_data.get("test_result", {})

        metadata = {
            "tier": test_result.get("tier", "unknown"),
            "message": test_result.get("message", ""),
        }

        success = await self.key_manager.store_user_key(user_id, provider_id, api_key, metadata)

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
            await query.edit_message_text("❌ Failed to save key. Please try again with /addkey")

        # Clear context
        context.user_data.clear()

        return int(ConversationHandler.END)

    async def cmd_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel current operation"""
        context.user_data.clear()
        await update.message.reply_text("❌ Operation cancelled.")
        return int(ConversationHandler.END)

    async def cmd_list_keys(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

    async def cmd_remove_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"Remove {provider_name}", callback_data=f"remove:{provider_id}"
                    )
                ]
            )

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text("Select provider to remove:", reply_markup=reply_markup)

    async def handle_remove_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle key removal callback"""
        query = update.callback_query
        await query.answer()

        user_id = str(update.effective_user.id)
        provider_id = query.data.split(":")[1]

        # Remove the key
        success = await self.key_manager.remove_user_key(user_id, provider_id)

        if success:
            await query.edit_message_text(
                f"✅ **{provider_id}** key removed successfully.\n\n"
                "Use /listkeys to see your remaining providers."
            )
            logger.info("Key removed", user_id=user_id, provider=provider_id)
        else:
            await query.edit_message_text(
                f"❌ Failed to remove {provider_id} key. Please try again."
            )

    async def cmd_test_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

    def _get_available_lessons(self) -> List[Tuple[str, str, str]]:
        """
        Get list of available lessons from the lessons directory.

        Returns:
            List of tuples: (lesson_id, title, difficulty)
        """
        lessons_path = Path(self.lesson_engine.lessons_path)
        lessons: List[Tuple[str, str, str]] = []

        if not lessons_path.exists():
            # Return default lessons if path doesn't exist
            return [
                ("stock_basics_001", "Understanding Stock Prices", "beginner"),
                ("stock_basics_002", "Market Orders vs Limit Orders", "beginner"),
                ("stock_basics_003", "Volume and Liquidity", "beginner"),
                ("valuation_001", "Understanding P/E Ratio", "intermediate"),
                ("risk_001", "Position Sizing and Risk", "intermediate"),
            ]

        # Scan lesson files
        lesson_files = sorted(lessons_path.glob("*.yaml"))
        for lesson_file in lesson_files:
            try:
                with open(lesson_file, "r") as f:
                    lesson_data = yaml.safe_load(f)
                    if lesson_data and isinstance(lesson_data, dict):
                        lesson_id = lesson_data.get("id", lesson_file.stem)
                        title = lesson_data.get("title", "Untitled Lesson")
                        difficulty = lesson_data.get("difficulty", "beginner")
                        lessons.append((lesson_id, title, difficulty))
            except Exception as e:
                logger.warning("Failed to load lesson file", file=str(lesson_file), error=str(e))

        return lessons

    def _get_lesson_id_to_file_map(self) -> Dict[str, str]:
        """
        Create a mapping from lesson IDs to their file paths.

        Returns:
            Dictionary mapping lesson_id to file path
        """
        lessons_path = Path(self.lesson_engine.lessons_path)
        mapping: Dict[str, str] = {}

        if not lessons_path.exists():
            return mapping

        for lesson_file in lessons_path.glob("*.yaml"):
            try:
                with open(lesson_file, "r") as f:
                    lesson_data = yaml.safe_load(f)
                    if lesson_data and isinstance(lesson_data, dict):
                        lesson_id = lesson_data.get("id", lesson_file.stem)
                        mapping[lesson_id] = str(lesson_file)
            except Exception:
                # Skip invalid lesson files silently - they'll be handled
                # when user tries to access them directly
                pass

        return mapping

    def _get_difficulty_emoji(self, difficulty: str) -> str:
        """Get emoji for difficulty level."""
        difficulty_emojis = {
            "beginner": "🟢",
            "intermediate": "🟡",
            "advanced": "🔴",
        }
        return difficulty_emojis.get(difficulty.lower(), "🟡")

    async def cmd_lesson(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show available lessons or continue current lesson"""
        user_id = str(update.effective_user.id)

        # Get user's progress
        progress = await self.lesson_engine.get_user_progress(user_id)
        completed = progress.get("completed", set())

        # Get available lessons dynamically
        lessons = self._get_available_lessons()

        # Limit to first 10 lessons for cleaner display
        # (Telegram callback data has a 64-byte limit)
        display_lessons = lessons[:10]

        text = "📚 **Available Lessons**\n\n"

        keyboard = []
        for lesson_id, title, difficulty in display_lessons:
            status = "✅" if lesson_id in completed else "📖"
            emoji = self._get_difficulty_emoji(difficulty)
            text += f"{status} {emoji} {title}\n"

            keyboard.append(
                [InlineKeyboardButton(f"{status} {title}", callback_data=f"lesson:{lesson_id}")]
            )

        total_lessons = len(lessons)
        text += f"\n💡 Tap a lesson to start! ({total_lessons} lessons available)"
        text += "\n\n🟢 Beginner | 🟡 Intermediate | 🔴 Advanced"

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    async def select_lesson(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle lesson selection"""
        query = update.callback_query
        await query.answer()

        user_id = str(update.effective_user.id)
        lesson_id = query.data.split(":")[1]

        # Try to load lesson from file path mapping first
        lesson = None
        lesson_file_map = self._get_lesson_id_to_file_map()

        if lesson_id in lesson_file_map:
            # Load from the mapped file path
            lesson = self.lesson_engine.load_lesson_from_file(lesson_file_map[lesson_id])

        if not lesson:
            # Try direct ID-based loading
            lesson = await self.lesson_engine.load_lesson(lesson_id)

        if not lesson:
            # Create sample lesson as fallback
            self.lesson_engine.create_sample_lesson(lesson_id)
            lesson = await self.lesson_engine.load_lesson(lesson_id)

        if not lesson:
            await query.edit_message_text("❌ Lesson not found. Please try again.")
            return

        # Render lesson
        rendered = await self.lesson_engine.render_lesson(lesson, user_id)

        # Mark as started
        self.lesson_engine.mark_lesson_started(user_id, lesson_id)

        # Update streak
        await self.gamification.update_streak(user_id)

        # Convert to string and handle Telegram's 4096 char limit
        content = str(rendered)
        max_length = 4000  # Leave some margin

        if len(content) > max_length:
            # Truncate with ellipsis
            content = (
                content[:max_length]
                + "\n\n...[Content truncated - lesson too long]\n\nUse /quiz to test your knowledge!"
            )

        # Send without Markdown parsing to avoid entity parsing errors
        await query.edit_message_text(content)

    async def cmd_quiz(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Start a quiz for current lesson"""
        user_id = str(update.effective_user.id)

        # Sample quiz questions
        questions = [
            {
                "id": "q1",
                "type": "multiple_choice",
                "text": "What is a stock?",
                "options": [
                    {"text": "A type of bond", "correct": False},
                    {"text": "Ownership in a company", "correct": True},
                    {"text": "A loan to a company", "correct": False},
                ],
                "correct_answer": "Ownership in a company",
                "xp_reward": 10,
            },
            {
                "id": "q2",
                "type": "true_false",
                "text": "P/E ratio compares a company's stock price to its earnings.",
                "options": [],
                "correct_answer": "true",
                "xp_reward": 10,
            },
        ]

        # Create quiz session
        session_id = self.quiz_system.create_session(user_id, "stock_basics", questions)
        context.user_data["quiz_session_id"] = session_id

        # Get first question
        session = self.quiz_system.get_session(session_id)
        if not session or not session.get("questions"):
            await update.message.reply_text("❌ Failed to start quiz.")
            return

        question = session["questions"][0]

        text = "📝 **Quiz Time!**\n\n"
        text += f"Question 1 of {len(session['questions'])}\n\n"
        text += f"❓ **{question['text']}**\n\n"

        keyboard = []
        if question["type"] == "multiple_choice":
            for i, opt in enumerate(question["options"]):
                # Use index instead of full text to avoid 64-byte callback limit
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            opt["text"], callback_data=f"quiz_answer:{session_id}:0:{i}"
                        )
                    ]
                )
        elif question["type"] == "true_false":
            keyboard = [
                [
                    InlineKeyboardButton("True", callback_data=f"quiz_answer:{session_id}:0:true"),
                    InlineKeyboardButton(
                        "False", callback_data=f"quiz_answer:{session_id}:0:false"
                    ),
                ]
            ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    async def handle_quiz_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle quiz answer submission"""
        query = update.callback_query
        await query.answer()

        user_id = str(update.effective_user.id)

        # Parse callback data: quiz_answer:session_id:question_index:answer_index_or_text
        parts = query.data.split(":")
        session_id = parts[1]
        question_idx = int(parts[2])
        answer_data = ":".join(parts[3:])  # Handle answers with colons

        # Get the session to access question options
        session = self.quiz_system.get_session(session_id)
        if not session:
            await query.edit_message_text("❌ Quiz session not found.")
            return

        questions = session.get("questions", [])
        if question_idx >= len(questions):
            await query.edit_message_text("❌ Invalid question.")
            return

        question = questions[question_idx]

        # Convert answer_data to actual answer text
        if question["type"] == "multiple_choice":
            # answer_data is an index for multiple choice
            try:
                opt_idx = int(answer_data)
                if opt_idx < len(question["options"]):
                    answer = question["options"][opt_idx]["text"]
                else:
                    await query.edit_message_text("❌ Invalid answer.")
                    return
            except ValueError:
                await query.edit_message_text("❌ Invalid answer format.")
                return
        else:
            # answer_data is the text itself for true/false
            answer = answer_data

        # Record answer
        result = self.quiz_system.answer_question(session_id, question_idx, answer)

        if "error" in result:
            await query.edit_message_text(f"❌ {result['error']}")
            return

        # Show result
        if result["correct"]:
            text = f"✅ **Correct!** +{result['xp_earned']} XP\n\n"
        else:
            text = f"❌ **Incorrect**\n{result.get('explanation', '')}\n\n"

        # Check if quiz complete
        score = self.quiz_system.get_quiz_score(session_id)
        # Re-fetch session for latest state
        session = self.quiz_system.get_session(session_id)

        if session and score:
            current_idx = session.get("current_question_index", question_idx + 1)
            total = score.get("total_questions", 1)

            if current_idx >= total or session.get("completed_at"):
                # Quiz complete
                text += "🎉 **Quiz Complete!**\n\n"
                text += f"Score: {score['correct_answers']}/{total} ({score['percentage']:.0f}%)\n"
                text += f"XP Earned: {score['total_xp']}\n\n"

                # Award XP
                await self.gamification.award_xp(user_id, "quiz_passed")

                text += "Use /lesson for more learning!"
                await query.edit_message_text(text, parse_mode="Markdown")
                return

            # Show next question
            questions = session.get("questions", [])
            if current_idx < len(questions):
                question = questions[current_idx]

                text += f"Question {current_idx + 1} of {total}\n\n"
                text += f"❓ **{question['text']}**\n\n"

                keyboard = []
                if question["type"] == "multiple_choice":
                    for i, opt in enumerate(question["options"]):
                        # Use index instead of text to avoid 64-byte callback limit
                        keyboard.append(
                            [
                                InlineKeyboardButton(
                                    opt["text"],
                                    callback_data=f"quiz_answer:{session_id}:{current_idx}:{i}",
                                )
                            ]
                        )
                elif question["type"] == "true_false":
                    keyboard = [
                        [
                            InlineKeyboardButton(
                                "True", callback_data=f"quiz_answer:{session_id}:{current_idx}:true"
                            ),
                            InlineKeyboardButton(
                                "False",
                                callback_data=f"quiz_answer:{session_id}:{current_idx}:false",
                            ),
                        ]
                    ]

                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text, reply_markup=reply_markup, parse_mode="Markdown"
                )
                return

        await query.edit_message_text(text, parse_mode="Markdown")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle general text messages (non-command)"""
        user_id = str(update.effective_user.id)
        message = update.message.text

        # Check if user has an active mentor session FIRST
        mentor_persona = context.user_data.get("mentor_persona")

        if mentor_persona:
            # User is chatting with a mentor - route to mentor service
            await update.message.reply_text("🤔 Thinking...")

            try:
                response = await self.mentor_service.respond(
                    user_id=user_id, question=message, persona=mentor_persona, context={}
                )

                response_text = f"{response['icon']} **{response['mentor']}**\n\n"
                response_text += response["text"]

                # Add suggested lessons if any
                if response.get("related_lessons"):
                    response_text += "\n\n📚 **Related lessons:**\n"
                    for lesson_id in response["related_lessons"]:
                        response_text += f"• {lesson_id}\n"

                await update.message.reply_text(response_text, parse_mode="Markdown")

            except Exception as e:
                logger.error("Failed to generate mentor response", error=str(e), user_id=user_id)
                await update.message.reply_text(
                    "❌ Sorry, I'm having trouble generating a response right now. "
                    "Please try again or use /help for other options."
                )
            return

        # Only check for greetings if NOT in mentor mode
        greetings = [
            "hi",
            "hello",
            "hey",
            "greetings",
            "good morning",
            "good afternoon",
            "good evening",
        ]
        if any(greeting in message.lower() for greeting in greetings):
            await update.message.reply_text(
                "👋 Hello! I'm the FIML Educational Bot.\n\n"
                "I can help you learn about trading and investing.\n\n"
                "Try these commands:\n"
                "• /help - See all commands\n"
                "• /lesson - Start learning\n"
                "• /mentor - Chat with AI mentor\n"
                "• /progress - View your progress",
                parse_mode="Markdown",
            )
            return

        # For other messages, suggest using mentor or commands
        await update.message.reply_text(
            "💬 I understand you want to chat!\n\n"
            "For educational conversations, try:\n"
            "• /mentor - Chat with an AI trading mentor\n"
            "• /help - See what I can do\n\n"
            "Or ask me about specific topics using /lesson",
            parse_mode="Markdown",
        )

    async def cmd_mentor(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Start AI mentor interaction"""
        text = """
🤖 **AI Mentor Selection**

Choose your learning companion:

👩‍🏫 Maya - Patient guide
Uses analogies, beginner-friendly

👨‍💼 Theo - Analytical expert
Data-driven, technical analysis

🧘‍♀️ Zara - Psychology coach
Trading discipline and mindset
"""

        keyboard = [
            [InlineKeyboardButton("👩‍🏫 Maya", callback_data="mentor:maya")],
            [InlineKeyboardButton("👨‍💼 Theo", callback_data="mentor:theo")],
            [InlineKeyboardButton("🧘‍♀️ Zara", callback_data="mentor:zara")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    async def select_mentor(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle mentor selection"""
        query = update.callback_query
        await query.answer()

        mentor_name = query.data.split(":")[1]

        # Map to persona
        persona_map = {
            "maya": MentorPersona.MAYA,
            "theo": MentorPersona.THEO,
            "zara": MentorPersona.ZARA,
        }
        persona = persona_map.get(mentor_name, MentorPersona.MAYA)

        # Store mentor preference
        context.user_data["mentor_persona"] = persona

        mentor_info = self.mentor_service.get_mentor_info(persona)

        text = f"""
{mentor_info['icon']} **{mentor_info['name']}** is ready to help!

{mentor_info['description']}

**Focus:** {mentor_info['focus']}

💬 Ask me anything about trading and investing!

_Type your question below, or use /help for commands._

📚 _Educational purposes only - not financial advice_
"""

        await query.edit_message_text(text, parse_mode="Markdown")

    async def cmd_progress(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show user's learning progress"""
        user_id = str(update.effective_user.id)

        # Get gamification summary
        summary = await self.gamification.get_user_summary(user_id)

        # Get lesson progress
        lesson_progress = await self.lesson_engine.get_user_progress(user_id)
        completed_lessons = len(lesson_progress.get("completed", set()))

        text = f"""
📊 **Your Learning Progress**

**Level:** {summary['level']} - {summary['level_title']}
**Total XP:** {summary['total_xp']} XP
**Streak:** {summary['streak_days']} days 🔥

**Lessons:**
✅ Completed: {completed_lessons}
📝 Quizzes: {summary.get('quizzes_completed', 0)}

**Badges:**
"""
        if summary["badges"]:
            for badge in summary["badges"]:
                text += f"{badge['icon']} {badge['name']}\n"
        else:
            text += "No badges yet - keep learning!\n"

        # Progress bar
        progress = summary.get("progress_to_next_level", {})
        if not progress.get("max_level"):
            percent = progress.get("progress", 0)
            bar_filled = int(percent / 10)
            bar_empty = 10 - bar_filled
            progress_bar = "█" * bar_filled + "░" * bar_empty

            text += f"\n**Next Level:** {progress.get('xp_needed', 0)} XP needed\n"
            text += f"[{progress_bar}] {percent:.0f}%"

        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_fkdsl(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /fkdsl command - FK-DSL query interface"""
        text = """
🔮 **Financial Knowledge DSL (FK-DSL)**

Execute advanced financial analysis queries using FIML's powerful DSL.

**What is FK-DSL?**
A specialized query language for multi-asset financial analysis:
• `EVALUATE` - Analyze single assets with multiple metrics
• `COMPARE` - Side-by-side comparison of assets
• `CORRELATE` - Correlation analysis between assets
• `SCAN` - Market screening with custom filters

**Choose a template to get started:**
"""

        # Create inline keyboard with templates
        keyboard = []
        for template_id, template_data in DSL_TEMPLATES.items():
            keyboard.append(
                [
                    InlineKeyboardButton(
                        template_data["display"], callback_data=f"dsl_template:{template_id}"
                    )
                ]
            )

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    async def handle_dsl_template(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle DSL template selection"""
        query = update.callback_query
        await query.answer()

        user_id = str(update.effective_user.id)
        template_id = query.data.split(":")[1]

        template = DSL_TEMPLATES.get(template_id)
        if not template:
            await query.edit_message_text("❌ Template not found.")
            return

        if template_id == "custom":
            # Custom query - ask user to send their query
            text = """
✏️ **Custom FK-DSL Query**

Send your query as a message. Examples:

`EVALUATE TSLA: PRICE, VOLATILITY(30d), CORRELATE(BTC)`

`COMPARE BTC, ETH, SOL BY VOLUME(7d), MOMENTUM`

`CORRELATE NVDA WITH AAPL, AMD WINDOW 60d`

`SCAN US_TECH WHERE PE < 25 AND MARKETCAP > 1000000000`

📚 **DSL Syntax:**
• Asset symbols: AAPL, BTC, ETH, etc.
• Metrics: PRICE, VOLUME, PE, MARKETCAP, VOLATILITY
• Time windows: 7d, 30d, 60d, 90d
• Operators: <, >, =, AND, OR

Type your query below or /cancel to abort.
"""
            await query.edit_message_text(text, parse_mode="Markdown")
            context.user_data["awaiting_dsl_query"] = True
            return

        # Show template with option to execute
        text = f"""
{template['display']}

**Description:** {template['description']}

**Query:**
```
{template['query']}
```

**Example:** {template['example']}

🔄 Executing query...
"""
        await query.edit_message_text(text, parse_mode="Markdown")

        # Execute the query
        await self.execute_user_dsl_query(
            update=update,
            context=context,
            user_id=user_id,
            query=template["query"],
            from_callback=True,
        )

    async def execute_user_dsl_query(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: str,
        query: str,
        from_callback: bool = False,
    ) -> None:
        """Execute FK-DSL query and display results"""

        try:
            # Execute DSL query (sync mode for immediate results)
            logger.info("Executing FK-DSL query", user_id=user_id, query=query)
            result = await execute_fk_dsl(query=query, async_execution=False)

            # Format the result
            formatted_message = await self.format_dsl_result(result, query)

            # Send result to user
            if from_callback:
                # Edit the existing message
                try:
                    await update.callback_query.message.reply_text(
                        formatted_message, parse_mode="Markdown"
                    )
                except Exception as e:
                    logger.warning("Failed to send as reply, sending new message", error=str(e))
                    await update.callback_query.message.chat.send_message(
                        formatted_message, parse_mode="Markdown"
                    )
            else:
                # Send new message
                await update.message.reply_text(formatted_message, parse_mode="Markdown")

            # Award XP for successful query
            if result.get("status") == "completed":
                xp_amount = 15  # Base XP for DSL query
                await self.gamification.award_xp(user_id, "dsl_query_completed")
                logger.info("Awarded XP for DSL query", user_id=user_id, xp=xp_amount)

        except Exception as e:
            error_message = f"""
❌ **Query Execution Failed**

**Error:** {str(e)}

**Your query:**
```
{query}
```

**Tips:**
• Check your syntax (EVALUATE, COMPARE, CORRELATE, SCAN)
• Verify asset symbols are valid
• Ensure metrics are supported

Try /fkdsl again to see examples!

⚠️ Educational purposes only — not financial advice.
"""
            logger.error("DSL query execution failed", user_id=user_id, query=query, error=str(e))

            if from_callback:
                await update.callback_query.message.reply_text(error_message, parse_mode="Markdown")
            else:
                await update.message.reply_text(error_message, parse_mode="Markdown")

    async def format_dsl_result(self, result: Dict[str, Any], query: str) -> str:
        """Format DSL execution result for Telegram display"""

        if result.get("status") == "failed":
            return f"""
❌ **Query Failed**

**Query:** `{query}`

**Error:** {result.get('error', 'Unknown error')}

Try /fkdsl for template examples!

⚠️ Educational purposes only — not financial advice.
"""

        if result.get("status") == "running":
            return f"""
🔄 **Query Running**

**Task ID:** `{result.get('task_id')}`

**Query:** `{query}`

**Progress:** {result.get('total_steps', 0)} steps

Use /status to check progress (coming soon).

⚠️ Educational purposes only — not financial advice.
"""

        # Status is "completed"
        query_text = result.get("query", query)
        result_data = result.get("result", {})

        # Start building formatted message
        message_parts = ["✅ **Query Completed**", "", f"**Query:** `{query_text}`", ""]

        # Format result data based on content
        if isinstance(result_data, dict):
            message_parts.append("**Results:**")
            message_parts.append("```")

            # Try to format as table or key-value pairs
            for key, value in result_data.items():
                if isinstance(value, dict):
                    message_parts.append(f"{key}:")
                    for sub_key, sub_value in value.items():
                        # Format numbers nicely
                        if isinstance(sub_value, (int, float)):
                            if isinstance(sub_value, float):
                                formatted_value = f"{sub_value:,.2f}"
                            else:
                                formatted_value = f"{sub_value:,}"
                            message_parts.append(f"  {sub_key}: {formatted_value}")
                        else:
                            message_parts.append(f"  {sub_key}: {sub_value}")
                else:
                    if isinstance(value, (int, float)):
                        if isinstance(value, float):
                            formatted_value = f"{value:,.2f}"
                        else:
                            formatted_value = f"{value:,}"
                        message_parts.append(f"{key}: {formatted_value}")
                    else:
                        message_parts.append(f"{key}: {value}")

            message_parts.append("```")
        else:
            # Fallback to JSON representation
            message_parts.append("**Results:**")
            message_parts.append("```json")
            message_parts.append(json.dumps(result_data, indent=2))
            message_parts.append("```")

        # Add metadata
        message_parts.extend(
            [
                "",
                "📊 **Data Quality:**",
                f"• Status: {result.get('status', 'unknown').title()}",
            ]
        )

        # Add educational note
        message_parts.extend(
            [
                "",
                "💡 **What's Next?**",
                "• Try modifying the query with different assets",
                "• Explore other DSL templates with /fkdsl",
                "• Check your progress with /progress",
                "",
                "⚠️ Educational purposes only — not financial advice.",
            ]
        )

        # Join all parts
        full_message = "\n".join(message_parts)

        # Check Telegram's 4096 character limit
        if len(full_message) > 4000:
            # Truncate and add notice
            full_message = (
                full_message[:3900]
                + "\n\n...\n\n[Results truncated due to length]\n\n⚠️ Educational purposes only — not financial advice."
            )

        return full_message

    async def start(self) -> None:
        """Start the bot"""
        logger.info("Starting Telegram bot...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        logger.info("Telegram bot started")

    async def stop(self) -> None:
        """Stop the bot"""
        logger.info("Stopping Telegram bot...")
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()
        logger.info("Telegram bot stopped")

    def run(self) -> None:
        """Run the bot (blocking)"""
        self.application.run_polling()
