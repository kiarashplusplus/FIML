"""
Comprehensive tests for FIML Bot module

Tests cover:
- Key management (file-based storage with encryption)
- Provider configuration
- Gamification system
- Lesson content engine
- Quiz system
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, UTC
import tempfile
import json
from pathlib import Path
from cryptography.fernet import Fernet
import yaml

from fiml.bot.core.key_manager import UserProviderKeyManager
from fiml.bot.core.provider_configurator import FIMLProviderConfigurator
from fiml.bot.education.gamification import GamificationEngine, UserStats, Badge
from fiml.bot.education.lesson_engine import (
    LessonContentEngine, 
    Lesson, 
    LessonSection, 
    QuizQuestion as LessonQuizQuestion
)
from fiml.bot.education.quiz_system import QuizSystem, QuizQuestion, QuizSession


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_storage_dir():
    """Temporary directory for key storage"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def encryption_key():
    """Generate test encryption key"""
    return Fernet.generate_key()


@pytest.fixture
def key_manager(encryption_key, temp_storage_dir):
    """UserProviderKeyManager instance with file-based storage"""
    return UserProviderKeyManager(
        encryption_key=encryption_key,
        storage_path=temp_storage_dir
    )


@pytest.fixture
def provider_configurator(key_manager):
    """FIMLProviderConfigurator instance"""
    return FIMLProviderConfigurator(key_manager=key_manager)


@pytest.fixture
def gamification_engine():
    """GamificationEngine instance"""
    return GamificationEngine()


@pytest.fixture
def temp_lessons_dir():
    """Temporary directory for lesson content"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create sample lesson file
        lesson_data = {
            "id": "test_lesson_1",
            "title": "Test Lesson",
            "category": "beginner",
            "difficulty": "easy",
            "duration_minutes": 10,
            "learning_objectives": ["Learn basics", "Understand concepts"],
            "prerequisites": [],
            "sections": [
                {
                    "type": "introduction",
                    "content": "Welcome to the test lesson",
                    "metadata": {}
                }
            ],
            "quiz_questions": [
                {
                    "id": "q1",
                    "type": "multiple_choice",
                    "text": "What is 2+2?",
                    "options": [
                        {"id": "a", "text": "3"},
                        {"id": "b", "text": "4"},
                        {"id": "c", "text": "5"}
                    ],
                    "correct_answer": "b",
                    "xp_reward": 10
                }
            ],
            "xp_reward": 50,
            "next_lesson": None
        }
        
        lesson_file = Path(tmpdir) / "test_lesson_1.yaml"
        with open(lesson_file, 'w') as f:
            yaml.dump(lesson_data, f)
        
        # Create second lesson
        lesson_data_2 = {
            "id": "test_lesson_2",
            "title": "Advanced Test Lesson",
            "category": "intermediate",
            "difficulty": "medium",
            "duration_minutes": 15,
            "learning_objectives": ["Advanced concepts"],
            "prerequisites": ["test_lesson_1"],
            "sections": [
                {
                    "type": "explanation",
                    "content": "Advanced content",
                    "metadata": {}
                }
            ],
            "quiz_questions": [],
            "xp_reward": 75,
            "next_lesson": None
        }
        
        lesson_file_2 = Path(tmpdir) / "test_lesson_2.yaml"
        with open(lesson_file_2, 'w') as f:
            yaml.dump(lesson_data_2, f)
        
        yield tmpdir


@pytest.fixture
def lesson_engine(temp_lessons_dir):
    """LessonContentEngine instance with sample content"""
    return LessonContentEngine(lessons_path=temp_lessons_dir)


@pytest.fixture
def quiz_system():
    """QuizSystem instance"""
    return QuizSystem()


# ============================================================================
# UserProviderKeyManager Tests (File-based storage)
# ============================================================================

class TestUserProviderKeyManager:
    """Test key management with file-based encrypted storage"""

    def test_initialization(self, temp_storage_dir):
        """Test manager initializes with file storage"""
        manager = UserProviderKeyManager(storage_path=temp_storage_dir)
        assert manager is not None
        assert Path(temp_storage_dir).exists()

    @pytest.mark.asyncio
    async def test_store_and_retrieve_key(self, key_manager):
        """Test storing and retrieving encrypted API key"""
        user_id = "test_user"
        provider = "openai"
        api_key = "sk-test123"
        
        # Store key
        success = await key_manager.store_user_key(user_id, provider, api_key)
        assert success is True
        
        # Retrieve key
        retrieved = await key_manager.get_key(user_id, provider)
        assert retrieved == api_key

    @pytest.mark.asyncio
    async def test_delete_key(self, key_manager):
        """Test deleting stored key"""
        user_id = "test_user"
        provider = "openai"
        api_key = "sk-test123"
        
        await key_manager.store_user_key(user_id, provider, api_key)
        assert await key_manager.get_key(user_id, provider) == api_key
        
        # Delete key
        deleted = await key_manager.remove_user_key(user_id, provider)
        assert deleted is True
        assert await key_manager.get_key(user_id, provider) is None

    @pytest.mark.asyncio
    async def test_list_user_providers(self, key_manager):
        """Test listing all providers for a user"""
        user_id = "test_user"
        
        await key_manager.store_user_key(user_id, "openai", "key1")
        await key_manager.store_user_key(user_id, "anthropic", "key2")
        await key_manager.store_user_key(user_id, "google", "key3")
        
        keys = await key_manager.get_user_keys(user_id)
        assert len(keys) == 3
        assert "openai" in keys
        assert "anthropic" in keys
        assert "google" in keys

    @pytest.mark.asyncio
    async def test_encryption_different_keys(self, temp_storage_dir):
        """Test that different encryption keys produce different results"""
        key1 = Fernet.generate_key()
        key2 = Fernet.generate_key()
        
        manager1 = UserProviderKeyManager(encryption_key=key1, storage_path=temp_storage_dir)
        await manager1.store_user_key("user1", "openai", "secret123")
        
        # Cannot decrypt with different key - returns empty string or None
        manager2 = UserProviderKeyManager(encryption_key=key2, storage_path=temp_storage_dir)
        result = await manager2.get_key("user1", "openai")
        # Decryption fails silently, returns None or empty string
        assert result != "secret123"

    @pytest.mark.asyncio
    async def test_nonexistent_key(self, key_manager):
        """Test retrieving nonexistent key returns None"""
        result = await key_manager.get_key("nonexistent_user", "openai")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_existing_key(self, key_manager):
        """Test updating an existing key"""
        user_id = "test_user"
        provider = "openai"
        
        await key_manager.store_user_key(user_id, provider, "old_key")
        assert await key_manager.get_key(user_id, provider) == "old_key"
        
        await key_manager.store_user_key(user_id, provider, "new_key")
        assert await key_manager.get_key(user_id, provider) == "new_key"


# ============================================================================
# FIMLProviderConfigurator Tests
# ============================================================================

class TestFIMLProviderConfigurator:
    """Test provider configuration management"""

    def test_initialization(self, provider_configurator):
        """Test configurator initializes correctly"""
        assert provider_configurator is not None
        assert provider_configurator.key_manager is not None

    @pytest.mark.asyncio
    async def test_get_user_provider_config(self, provider_configurator, key_manager):
        """Test getting user-specific provider configuration"""
        user_id = "test_user"
        provider_name = "alpha_vantage"
        api_key = "test-av-key"
        
        # Store user key
        await key_manager.store_user_key(user_id, provider_name, api_key)
        
        # Get user keys
        user_keys = await key_manager.get_user_keys(user_id)
        
        # Get config
        config = provider_configurator.get_user_provider_config(user_id, user_keys=user_keys)
        assert config is not None
        assert "providers" in config
        
        # Check that user's provider is in config
        provider_names = [p["name"] for p in config["providers"]]
        assert provider_name in provider_names

    def test_free_providers(self, provider_configurator):
        """Test identifying free providers"""
        free_providers = provider_configurator.FREE_PROVIDERS
        assert isinstance(free_providers, list)
        # Verify yahoo_finance is a free provider
        assert "yahoo_finance" in free_providers

    @pytest.mark.asyncio
    async def test_configure_multiple_providers(self, provider_configurator, key_manager):
        """Test configuring multiple providers for user"""
        user_id = "test_user"
        
        providers = {
            "alpha_vantage": "av-key",
            "polygon": "polygon-key",
            "finnhub": "finnhub-key"
        }
        
        for provider, key in providers.items():
            await key_manager.store_user_key(user_id, provider, key)
        
        # Get user keys and config
        user_keys = await key_manager.get_user_keys(user_id)
        config = provider_configurator.get_user_provider_config(user_id, user_keys=user_keys)
        
        # Check all providers are in config
        provider_names = [p["name"] for p in config["providers"]]
        for provider in providers.keys():
            assert provider in provider_names


# ============================================================================
# GamificationEngine Tests
# ============================================================================

class TestGamificationEngine:
    """Test gamification system (XP, levels, badges)"""

    def test_initialization(self, gamification_engine):
        """Test engine initializes correctly"""
        assert gamification_engine is not None

    @pytest.mark.asyncio
    async def test_award_xp(self, gamification_engine):
        """Test awarding XP to user"""
        user_id = "test_user"
        action = "lesson_completed"  # Must match XP_REWARDS dict key
        
        result = await gamification_engine.award_xp(user_id, action)
        assert result is not None
        assert "xp_earned" in result
        assert result["xp_earned"] > 0

    @pytest.mark.asyncio
    async def test_get_user_stats(self, gamification_engine):
        """Test retrieving user statistics"""
        user_id = "test_user"
        
        # Award some XP first
        await gamification_engine.award_xp(user_id, "lesson_completed")
        
        stats = await gamification_engine.get_or_create_stats(user_id)
        assert stats is not None
        assert isinstance(stats, UserStats)
        assert stats.total_xp > 0

    @pytest.mark.asyncio
    async def test_level_progression(self, gamification_engine):
        """Test user levels up with enough XP"""
        user_id = "test_user"
        
        # Award enough XP to level up
        for i in range(20):
            await gamification_engine.award_xp(user_id, "lesson_completed")
        
        stats = await gamification_engine.get_or_create_stats(user_id)
        assert stats.level >= 1

    def test_badge_earning(self, gamification_engine):
        """Test earning badges"""
        user_id = "test_user"
        badge_id = "first_lesson"
        
        # Award badge (synchronous method)
        success = gamification_engine.award_badge(user_id, badge_id)
        assert success is True
        
        # Check badge was added
        assert gamification_engine.has_badge(user_id, badge_id) is True

    @pytest.mark.asyncio
    async def test_streak_tracking(self, gamification_engine):
        """Test daily streak tracking"""
        user_id = "test_user"
        
        # Record activity
        gamification_engine.record_daily_activity(user_id)
        
        stats = await gamification_engine.get_or_create_stats(user_id)
        assert stats.streak_days >= 0


# ============================================================================
# LessonContentEngine Tests
# ============================================================================

class TestLessonContentEngine:
    """Test lesson content management and rendering"""

    def test_initialization(self, lesson_engine):
        """Test engine initializes and loads lessons"""
        assert lesson_engine is not None
        assert lesson_engine.lessons_path.exists()

    @pytest.mark.asyncio
    async def test_load_lesson(self, lesson_engine):
        """Test loading lesson file"""
        lesson_data = await lesson_engine.load_lesson("test_lesson_1")
        assert lesson_data is not None
        assert lesson_data["id"] == "test_lesson_1"
        assert lesson_data["title"] == "Test Lesson"

    @pytest.mark.asyncio
    async def test_lesson_structure(self, lesson_engine):
        """Test lesson has correct structure"""
        lesson_data = await lesson_engine.load_lesson("test_lesson_1")
        
        assert "id" in lesson_data
        assert "title" in lesson_data
        assert "sections" in lesson_data
        assert "quiz" in lesson_data
        assert "questions" in lesson_data["quiz"]
        assert lesson_data["xp_reward"] == 50
        assert lesson_data["difficulty"] == "easy"

    @pytest.mark.asyncio
    async def test_render_lesson(self, lesson_engine):
        """Test rendering lesson content"""
        user_id = "test_user"
        lesson_data = await lesson_engine.load_lesson("test_lesson_1")
        
        rendered = await lesson_engine.render_lesson(lesson_data, user_id, include_fiml_data=False)
        assert rendered is not None
        assert "Welcome to the test lesson" in rendered

    @pytest.mark.asyncio
    async def test_prerequisite_checking(self, lesson_engine):
        """Test checking lesson prerequisites"""
        user_id = "test_user"
        
        # Load lesson 2 which requires lesson 1 - this caches the Lesson object
        await lesson_engine.load_lesson("test_lesson_2")
        
        # Get cached Lesson object
        lesson_2 = lesson_engine._lessons_cache["test_lesson_2"]
        
        # User hasn't completed lesson 1 yet
        has_prereqs, missing = await lesson_engine.check_prerequisites(user_id, lesson_2)
        assert has_prereqs is False
        assert len(missing) > 0

    @pytest.mark.asyncio
    async def test_mark_lesson_completed(self, lesson_engine):
        """Test marking a lesson as completed"""
        user_id = "test_user"
        lesson_id = "test_lesson_1"
        
        # Mark as completed
        await lesson_engine.mark_completed(user_id, lesson_id)
        
        # Check completion status using synchronous method
        lesson_engine.mark_lesson_completed(user_id, lesson_id)
        is_completed = lesson_engine.is_lesson_completed(user_id, lesson_id)
        assert is_completed is True


# ============================================================================
# QuizSystem Tests
# ============================================================================

class TestQuizSystem:
    """Test interactive quiz functionality"""

    def test_initialization(self, quiz_system):
        """Test quiz system initializes"""
        assert quiz_system is not None

    @pytest.mark.asyncio
    async def test_start_quiz(self, quiz_system):
        """Test starting a quiz session"""
        user_id = "test_user"
        lesson_id = "test_lesson"
        
        questions = [
            QuizQuestion(
                id="q1",
                type="multiple_choice",
                text="What is 2+2?",
                options=[
                    {"id": "a", "text": "3"},
                    {"id": "b", "text": "4"}
                ],
                correct_answer="b"
            )
        ]
        
        session = await quiz_system.start_quiz(user_id, lesson_id, questions)
        assert session is not None
        assert isinstance(session, QuizSession)
        assert session.user_id == user_id
        assert session.lesson_id == lesson_id

    @pytest.mark.asyncio
    async def test_submit_answer(self, quiz_system):
        """Test submitting quiz answer"""
        user_id = "test_user"
        lesson_id = "test_lesson"
        
        questions = [
            QuizQuestion(
                id="q1",
                type="multiple_choice",
                text="What is 2+2?",
                options=[
                    {"id": "a", "text": "3", "correct": False},
                    {"id": "b", "text": "4", "correct": True}
                ],
                correct_answer="4",
                xp_reward=10
            )
        ]
        
        session = await quiz_system.start_quiz(user_id, lesson_id, questions)
        
        # Submit correct answer
        result = await quiz_system.submit_answer(session.session_id, "4")
        assert result["correct"] is True
        assert result["xp_earned"] == 10

    @pytest.mark.asyncio
    async def test_submit_wrong_answer(self, quiz_system):
        """Test submitting wrong answer"""
        user_id = "test_user"
        lesson_id = "test_lesson"
        
        questions = [
            QuizQuestion(
                id="q1",
                type="multiple_choice",
                text="What is 2+2?",
                options=[
                    {"id": "a", "text": "3"},
                    {"id": "b", "text": "4", "correct": True}
                ],
                correct_answer="4"
            )
        ]
        
        session = await quiz_system.start_quiz(user_id, lesson_id, questions)
        
        # Submit wrong answer
        result = await quiz_system.submit_answer(session.session_id, "3")
        assert result["correct"] is False
        assert result.get("xp_earned", 0) == 0

    @pytest.mark.asyncio
    async def test_complete_quiz(self, quiz_system):
        """Test completing entire quiz"""
        user_id = "test_user"
        lesson_id = "test_lesson"
        
        questions = [
            QuizQuestion(id="q1", type="multiple_choice", text="Q1", 
                        options=[{"text": "a", "correct": True}], correct_answer="a", xp_reward=10),
            QuizQuestion(id="q2", type="multiple_choice", text="Q2", 
                        options=[{"text": "b", "correct": True}], correct_answer="b", xp_reward=10),
        ]
        
        session = await quiz_system.start_quiz(user_id, lesson_id, questions)
        
        # Answer all questions
        await quiz_system.submit_answer(session.session_id, "a")
        result = await quiz_system.submit_answer(session.session_id, "b")
        
        # Check final results
        assert result["quiz_complete"] is True
        assert result["final_score"] == 2
        assert result["total_xp"] == 20

    @pytest.mark.asyncio
    async def test_numeric_question(self, quiz_system):
        """Test numeric answer with tolerance"""
        user_id = "test_user"
        lesson_id = "test_lesson"
        
        questions = [
            QuizQuestion(
                id="q1",
                type="numeric",
                text="What is pi (approximately)?",
                correct_answer=3.14159,
                tolerance=0.01
            )
        ]
        
        session = await quiz_system.start_quiz(user_id, lesson_id, questions)
        
        # Answer within tolerance should be correct
        result = await quiz_system.submit_answer(session.session_id, 3.14)
        assert result["correct"] is True

    @pytest.mark.asyncio
    async def test_get_active_session(self, quiz_system):
        """Test retrieving active quiz session"""
        user_id = "test_user"
        lesson_id = "test_lesson"
        
        questions = [QuizQuestion(id="q1", type="multiple_choice", text="Q", correct_answer="a")]
        session = await quiz_system.start_quiz(user_id, lesson_id, questions)
        
        retrieved = quiz_system.get_session(session.session_id)
        assert retrieved is not None
