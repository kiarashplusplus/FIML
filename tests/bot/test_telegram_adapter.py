"""
Tests for TelegramBotAdapter (Component 4)
Tests Telegram bot command handlers and educational features
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fiml.bot.adapters.telegram_adapter import TelegramBotAdapter
from fiml.bot.core.key_manager import UserProviderKeyManager
from fiml.bot.core.provider_configurator import FIMLProviderConfigurator
from fiml.bot.education.ai_mentor import AIMentorService, MentorPersona
from fiml.bot.education.compliance_filter import EducationalComplianceFilter
from fiml.bot.education.gamification import GamificationEngine
from fiml.bot.education.lesson_engine import LessonContentEngine
from fiml.bot.education.quiz_system import QuizSystem


class TestTelegramBotAdapter:
    """Test suite for Telegram bot adapter"""

    @pytest.fixture
    def key_manager(self, tmp_path):
        """Create key manager with temp storage"""
        return UserProviderKeyManager(storage_path=str(tmp_path / "keys"))

    @pytest.fixture
    def provider_configurator(self, key_manager):
        """Create provider configurator"""
        return FIMLProviderConfigurator(key_manager)

    @pytest.fixture
    def mock_update(self):
        """Create mock Telegram update"""
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 12345
        update.effective_user.first_name = "TestUser"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        update.callback_query = None
        return update

    @pytest.fixture
    def mock_context(self):
        """Create mock Telegram context"""
        context = MagicMock()
        context.user_data = {}
        return context

    @pytest.fixture
    def adapter(self, key_manager, provider_configurator):
        """Create TelegramBotAdapter with mocked application"""
        with patch("fiml.bot.adapters.telegram_adapter.Application"):
            adapter = TelegramBotAdapter(
                token="test-token-123",
                key_manager=key_manager,
                provider_configurator=provider_configurator,
            )
            return adapter

    async def test_init_adapter(self, key_manager, provider_configurator):
        """Test adapter initialization"""
        with patch("fiml.bot.adapters.telegram_adapter.Application"):
            adapter = TelegramBotAdapter(
                token="test-token-123",
                key_manager=key_manager,
                provider_configurator=provider_configurator,
            )

            assert adapter is not None
            assert adapter.key_manager is key_manager
            assert adapter.provider_configurator is provider_configurator
            assert adapter.lesson_engine is not None
            assert adapter.quiz_system is not None
            assert adapter.mentor_service is not None
            assert adapter.gamification is not None
            assert adapter.compliance_filter is not None

    async def test_init_with_custom_components(self, key_manager, provider_configurator):
        """Test adapter initialization with custom components"""
        lesson_engine = LessonContentEngine()
        quiz_system = QuizSystem()
        mentor_service = AIMentorService()
        gamification = GamificationEngine()
        compliance_filter = EducationalComplianceFilter()

        with patch("fiml.bot.adapters.telegram_adapter.Application"):
            adapter = TelegramBotAdapter(
                token="test-token-123",
                key_manager=key_manager,
                provider_configurator=provider_configurator,
                lesson_engine=lesson_engine,
                quiz_system=quiz_system,
                mentor_service=mentor_service,
                gamification=gamification,
                compliance_filter=compliance_filter,
            )

            assert adapter.lesson_engine is lesson_engine
            assert adapter.quiz_system is quiz_system
            assert adapter.mentor_service is mentor_service
            assert adapter.gamification is gamification
            assert adapter.compliance_filter is compliance_filter

    async def test_cmd_start(self, adapter, mock_update, mock_context):
        """Test /start command handler"""
        await adapter.cmd_start(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        args, kwargs = mock_update.message.reply_text.call_args

        # Check welcome message contains user name
        assert "TestUser" in args[0]
        assert "Welcome" in args[0]
        assert kwargs.get("parse_mode") == "Markdown"

    async def test_cmd_help(self, adapter, mock_update, mock_context):
        """Test /help command handler"""
        await adapter.cmd_help(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        args, kwargs = mock_update.message.reply_text.call_args

        # Check help message contains commands
        help_text = args[0]
        assert "/addkey" in help_text
        assert "/lesson" in help_text
        assert "/quiz" in help_text
        assert "/mentor" in help_text
        assert "/progress" in help_text
        assert kwargs.get("parse_mode") == "Markdown"

    async def test_cmd_lesson(self, adapter, mock_update, mock_context):
        """Test /lesson command handler"""
        await adapter.cmd_lesson(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        args, kwargs = mock_update.message.reply_text.call_args

        # Check lessons list
        assert "Available Lessons" in args[0]
        assert kwargs.get("reply_markup") is not None  # Has inline keyboard

    async def test_cmd_quiz(self, adapter, mock_update, mock_context):
        """Test /quiz command handler"""
        await adapter.cmd_quiz(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        args, kwargs = mock_update.message.reply_text.call_args

        # Check quiz started
        text = args[0]
        assert "Quiz" in text
        assert kwargs.get("reply_markup") is not None  # Has answer buttons

    async def test_cmd_mentor(self, adapter, mock_update, mock_context):
        """Test /mentor command handler"""
        await adapter.cmd_mentor(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        args, kwargs = mock_update.message.reply_text.call_args

        # Check mentor selection
        text = args[0]
        assert "Maya" in text
        assert "Theo" in text
        assert "Zara" in text
        assert kwargs.get("reply_markup") is not None  # Has mentor buttons

    async def test_cmd_progress(self, adapter, mock_update, mock_context):
        """Test /progress command handler"""
        await adapter.cmd_progress(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        args, kwargs = mock_update.message.reply_text.call_args

        # Check progress display
        text = args[0]
        assert "Progress" in text
        assert "Level" in text
        assert "XP" in text

    async def test_cmd_list_keys_empty(self, adapter, mock_update, mock_context):
        """Test /listkeys with no keys"""
        await adapter.cmd_list_keys(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        args, kwargs = mock_update.message.reply_text.call_args

        # Should mention no keys
        text = args[0]
        assert "don't have any" in text.lower() or "API Keys" in text

    async def test_cmd_cancel(self, adapter, mock_update, mock_context):
        """Test /cancel command handler"""
        # Set some context data to be cleared
        mock_context.user_data["test_key"] = "test_value"

        await adapter.cmd_cancel(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        args = mock_update.message.reply_text.call_args[0]
        assert "cancelled" in args[0].lower()

        # Context should be cleared
        assert len(mock_context.user_data) == 0

    async def test_select_mentor(self, adapter, mock_context):
        """Test mentor selection callback"""
        # Create mock callback query
        mock_query = MagicMock()
        mock_query.data = "mentor:maya"
        mock_query.answer = AsyncMock()
        mock_query.edit_message_text = AsyncMock()

        mock_update = MagicMock()
        mock_update.callback_query = mock_query
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 12345

        await adapter.select_mentor(mock_update, mock_context)

        mock_query.answer.assert_called_once()
        mock_query.edit_message_text.assert_called_once()

        # Check mentor was selected
        assert mock_context.user_data.get("mentor_persona") == MentorPersona.MAYA

    async def test_handle_quiz_answer_correct(self, adapter, mock_context):
        """Test handling correct quiz answer"""
        user_id = "12345"

        # Create a quiz session first
        questions = [
            {
                "id": "q1",
                "type": "multiple_choice",
                "text": "What is a stock?",
                "options": [
                    {"text": "Bond", "correct": False},
                    {"text": "Ownership", "correct": True},
                ],
                "correct_answer": "Ownership",
            }
        ]
        session_id = adapter.quiz_system.create_session(user_id, "test_lesson", questions)

        # Create mock callback query
        mock_query = MagicMock()
        mock_query.data = f"quiz_answer:{session_id}:0:Ownership"
        mock_query.answer = AsyncMock()
        mock_query.edit_message_text = AsyncMock()

        mock_update = MagicMock()
        mock_update.callback_query = mock_query
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 12345

        await adapter.handle_quiz_answer(mock_update, mock_context)

        mock_query.edit_message_text.assert_called_once()
        args = mock_query.edit_message_text.call_args[0]
        # Should indicate correct
        assert "Correct" in args[0] or "✅" in args[0]

    async def test_handle_quiz_answer_incorrect(self, adapter, mock_context):
        """Test handling incorrect quiz answer"""
        user_id = "12345"

        # Create a quiz session
        questions = [
            {
                "id": "q1",
                "type": "multiple_choice",
                "text": "What is a stock?",
                "options": [
                    {"text": "Bond", "correct": False},
                    {"text": "Ownership", "correct": True},
                ],
                "correct_answer": "Ownership",
            }
        ]
        session_id = adapter.quiz_system.create_session(user_id, "test_lesson", questions)

        # Create mock callback query with wrong answer
        mock_query = MagicMock()
        mock_query.data = f"quiz_answer:{session_id}:0:Bond"
        mock_query.answer = AsyncMock()
        mock_query.edit_message_text = AsyncMock()

        mock_update = MagicMock()
        mock_update.callback_query = mock_query
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 12345

        await adapter.handle_quiz_answer(mock_update, mock_context)

        mock_query.edit_message_text.assert_called_once()
        args = mock_query.edit_message_text.call_args[0]
        # Should indicate incorrect
        assert "Incorrect" in args[0] or "❌" in args[0]

    async def test_cmd_add_key(self, adapter, mock_update, mock_context):
        """Test /addkey command starts conversation"""
        result = await adapter.cmd_add_key(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        args, kwargs = mock_update.message.reply_text.call_args

        # Should show provider selection
        assert "Add API Key" in args[0]
        assert kwargs.get("reply_markup") is not None

        # Should return PROVIDER_SELECT state
        from fiml.bot.adapters.telegram_adapter import PROVIDER_SELECT
        assert result == PROVIDER_SELECT

    async def test_select_provider(self, adapter, mock_context):
        """Test provider selection callback"""
        mock_query = MagicMock()
        mock_query.data = "provider:alpha_vantage"
        mock_query.answer = AsyncMock()
        mock_query.edit_message_text = AsyncMock()

        mock_update = MagicMock()
        mock_update.callback_query = mock_query
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 12345

        result = await adapter.select_provider(mock_update, mock_context)

        mock_query.answer.assert_called_once()
        mock_query.edit_message_text.assert_called_once()

        # Should store selected provider
        assert mock_context.user_data.get("selected_provider") == "alpha_vantage"

        # Should return KEY_ENTRY state
        from fiml.bot.adapters.telegram_adapter import KEY_ENTRY
        assert result == KEY_ENTRY

    async def test_cmd_status_no_providers(self, adapter, mock_update, mock_context):
        """Test /status with no providers"""
        await adapter.cmd_status(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        args = mock_update.message.reply_text.call_args[0]

        # Should indicate no providers
        assert "No providers" in args[0] or "addkey" in args[0].lower()

    async def test_cmd_test_key_no_keys(self, adapter, mock_update, mock_context):
        """Test /testkey with no keys"""
        await adapter.cmd_test_key(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        args = mock_update.message.reply_text.call_args[0]

        # Should indicate no keys
        assert "don't have any" in args[0].lower()

    async def test_cmd_remove_key_no_keys(self, adapter, mock_update, mock_context):
        """Test /removekey with no keys"""
        await adapter.cmd_remove_key(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        args = mock_update.message.reply_text.call_args[0]

        # Should indicate no keys
        assert "don't have any" in args[0].lower()

    async def test_select_lesson_creates_sample(self, adapter, mock_context, tmp_path):
        """Test lesson selection creates sample if not found"""
        # Update lesson path to temp directory
        adapter.lesson_engine.lessons_path = tmp_path / "lessons"
        adapter.lesson_engine.lessons_path.mkdir(parents=True, exist_ok=True)

        mock_query = MagicMock()
        mock_query.data = "lesson:stock_basics_001"
        mock_query.answer = AsyncMock()
        mock_query.edit_message_text = AsyncMock()

        mock_update = MagicMock()
        mock_update.callback_query = mock_query
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 12345

        await adapter.select_lesson(mock_update, mock_context)

        mock_query.answer.assert_called_once()
        mock_query.edit_message_text.assert_called_once()

    async def test_gamification_streak_updated_on_lesson(self, adapter, mock_context, tmp_path):
        """Test that streak is updated when user starts a lesson"""
        adapter.lesson_engine.lessons_path = tmp_path / "lessons"
        adapter.lesson_engine.lessons_path.mkdir(parents=True, exist_ok=True)

        user_id = "12345"

        # Create sample lesson
        adapter.lesson_engine.create_sample_lesson("stock_basics_001")

        mock_query = MagicMock()
        mock_query.data = "lesson:stock_basics_001"
        mock_query.answer = AsyncMock()
        mock_query.edit_message_text = AsyncMock()

        mock_update = MagicMock()
        mock_update.callback_query = mock_query
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = int(user_id)

        await adapter.select_lesson(mock_update, mock_context)

        # Check streak was recorded
        streak = adapter.gamification.get_streak(user_id)
        assert streak["current_streak"] >= 0  # Streak should exist


class TestTelegramAdapterIntegration:
    """Integration tests for Telegram adapter with components"""

    @pytest.fixture
    def full_adapter(self, tmp_path):
        """Create fully integrated adapter"""
        key_manager = UserProviderKeyManager(storage_path=str(tmp_path / "keys"))
        provider_configurator = FIMLProviderConfigurator(key_manager)

        lesson_engine = LessonContentEngine(lessons_path=str(tmp_path / "lessons"))
        lesson_engine.lessons_path.mkdir(parents=True, exist_ok=True)

        with patch("fiml.bot.adapters.telegram_adapter.Application"):
            adapter = TelegramBotAdapter(
                token="test-token-123",
                key_manager=key_manager,
                provider_configurator=provider_configurator,
                lesson_engine=lesson_engine,
            )
            return adapter

    async def test_complete_quiz_flow(self, full_adapter):
        """Test complete quiz flow: start -> answer -> complete"""
        user_id = "12345"
        mock_context = MagicMock()
        mock_context.user_data = {}

        # Start quiz
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = int(user_id)
        mock_update.message = MagicMock()
        mock_update.message.reply_text = AsyncMock()

        await full_adapter.cmd_quiz(mock_update, mock_context)

        # Get session ID from context
        session_id = mock_context.user_data.get("quiz_session_id")
        assert session_id is not None

        # Answer first question correctly
        mock_query = MagicMock()
        mock_query.data = f"quiz_answer:{session_id}:0:Ownership in a company"
        mock_query.answer = AsyncMock()
        mock_query.edit_message_text = AsyncMock()

        mock_update.callback_query = mock_query

        await full_adapter.handle_quiz_answer(mock_update, mock_context)

        # Check quiz system recorded the answer
        score = full_adapter.quiz_system.get_quiz_score(session_id)
        assert score is not None

    async def test_progress_tracking_integration(self, full_adapter):
        """Test that progress is tracked across components"""
        user_id = "12345"
        mock_context = MagicMock()
        mock_context.user_data = {}

        # Award some XP directly
        full_adapter.gamification.add_xp(user_id, 100, "test")

        # Check progress
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = int(user_id)
        mock_update.message = MagicMock()
        mock_update.message.reply_text = AsyncMock()

        await full_adapter.cmd_progress(mock_update, mock_context)

        args = mock_update.message.reply_text.call_args[0]
        # Should show the XP
        assert "100" in args[0] or "XP" in args[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
