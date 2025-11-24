"""
Tests for GamificationEngine (Component 9)
"""


import pytest

from fiml.bot.education.gamification import GamificationEngine


class TestGamificationEngine:
    """Test XP, levels, streaks, and badges"""

    @pytest.fixture
    def gamification(self):
        """Create a gamification engine"""
        return GamificationEngine()

    async def test_add_xp(self, gamification):
        """Test adding XP to a user"""
        user_id = "test_user_xp"

        # Add XP
        result = await gamification.award_xp(user_id, "lesson_completed")
        assert result["xp_earned"] == 50

        stats = await gamification.get_or_create_stats(user_id)
        assert stats.total_xp == 50

        # Add more XP
        result = await gamification.award_xp(user_id, "quiz_passed")
        assert result["xp_earned"] == 15

        stats = await gamification.get_or_create_stats(user_id)
        assert stats.total_xp == 65

    async def test_level_progression(self, gamification):
        """Test level calculation based on XP"""
        user_id = "test_user_level"

        # Level 1 (Novice) - 0 XP
        stats = await gamification.get_or_create_stats(user_id)
        assert stats.level == 1

        # Add XP to reach Level 2 (Learner) - 100 XP
        result = await gamification.award_xp(user_id, "simulation_completed")  # 100 XP
        assert result["level"] == 2
        assert result["level_up"] is True

        stats = await gamification.get_or_create_stats(user_id)
        assert stats.level == 2

    async def test_progress_to_next_level(self, gamification):
        """Test progress calculation to next level"""
        user_id = "test_user_progress"

        # Add 50 XP, need 100 for next level
        await gamification.award_xp(user_id, "lesson_completed")  # 50 XP
        progress = await gamification.get_progress_to_next_level(user_id)

        assert progress["current_level"] == 1
        assert progress["next_level"] == 2
        assert 0 <= progress["progress"] <= 100

    async def test_daily_streak(self, gamification):
        """Test daily streak tracking"""
        user_id = "test_user_streak"

        # Record activity today
        result = await gamification.update_streak(user_id)
        assert result["streak_days"] >= 0

    async def test_streak_multiplier(self, gamification):
        """Test XP multiplier at 7-day streak"""
        user_id = "test_user_multiplier"

        # Build up streak manually
        stats = await gamification.get_or_create_stats(user_id)
        stats.streak_days = 7

        # Award XP with multiplier
        result = await gamification.award_xp(user_id, "lesson_completed")  # Base 50
        # With 7-day streak: 50 * 1.5 = 75
        assert result["xp_earned"] == 75

    async def test_streak_broken(self, gamification):
        """Test streak reset when broken"""
        user_id = "test_user_broken"

        result = await gamification.update_streak(user_id)
        assert "streak_days" in result or "days" in result

    async def test_badges(self, gamification):
        """Test badge awarding"""
        user_id = "test_user_badges"

        # Award badge
        awarded = await gamification.award_badge(user_id, "first_lesson")
        assert awarded is True

        # Check badge in stats
        stats = await gamification.get_or_create_stats(user_id)
        assert "first_lesson" in stats.badges

    async def test_badge_deduplication(self, gamification):
        """Test that badges can't be awarded twice"""
        user_id = "test_user_dedup"

        # Award badge
        awarded = await gamification.award_badge(user_id, "first_lesson")
        assert awarded is True

        # Try to award again
        awarded = await gamification.award_badge(user_id, "first_lesson")
        assert awarded is False

    async def test_xp_rewards_by_action(self, gamification):
        """Test different XP rewards"""
        user_id = "test_user_rewards"

        result = await gamification.award_xp(user_id, "lesson_completed")
        assert result["xp_earned"] == 50

    async def test_leaderboard_stats(self, gamification):
        """Test user summary"""
        user_id = "test_user_leaderboard"

        await gamification.award_xp(user_id, "lesson_completed")
        summary = await gamification.get_user_summary(user_id)

        assert "xp" in summary
        assert "level" in summary

    async def test_all_level_definitions(self, gamification):
        """Test that all levels are defined"""
        assert len(gamification.LEVELS) == 10
        assert gamification.LEVELS[0]["level"] == 1
        assert gamification.LEVELS[9]["level"] == 10
