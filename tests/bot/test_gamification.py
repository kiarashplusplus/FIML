"""
Tests for GamificationEngine (Component 9)
"""

import pytest
from datetime import datetime, timedelta
from fiml.bot.education.gamification import GamificationEngine


class TestGamificationEngine:
    """Test XP, levels, streaks, and badges"""
    
    @pytest.fixture
    def gamification(self):
        """Create a gamification engine"""
        return GamificationEngine()
    
    def test_add_xp(self, gamification):
        """Test adding XP to a user"""
        user_id = "test_user_xp"
        
        # Add XP
        gamification.add_xp(user_id, 50, "lesson_complete")
        xp = gamification.get_user_xp(user_id)
        assert xp == 50
        
        # Add more XP
        gamification.add_xp(user_id, 30, "quiz_complete")
        xp = gamification.get_user_xp(user_id)
        assert xp == 80
    
    def test_level_progression(self, gamification):
        """Test level calculation based on XP"""
        user_id = "test_user_level"
        
        # Level 1 (Novice) - 0 XP
        level = gamification.get_user_level(user_id)
        assert level["level"] == 1
        assert level["name"] == "Novice"
        
        # Add XP to reach Level 2 (Learner) - 100 XP
        gamification.add_xp(user_id, 100, "test")
        level = gamification.get_user_level(user_id)
        assert level["level"] == 2
        assert level["name"] == "Learner"
        
        # Add more XP to reach Level 3 (Student) - 250 XP total
        gamification.add_xp(user_id, 150, "test")
        level = gamification.get_user_level(user_id)
        assert level["level"] == 3
        assert level["name"] == "Student"
    
    def test_progress_to_next_level(self, gamification):
        """Test progress calculation to next level"""
        user_id = "test_user_progress"
        
        # Start at 0 XP, need 100 for next level
        gamification.add_xp(user_id, 50, "test")
        progress = gamification.get_progress_to_next_level(user_id)
        
        assert progress["current_xp"] == 50
        assert progress["xp_for_next_level"] == 100
        assert progress["xp_needed"] == 50
        assert progress["percentage"] == 50.0
    
    def test_daily_streak(self, gamification):
        """Test daily streak tracking"""
        user_id = "test_user_streak"
        
        # Record activity today
        gamification.record_daily_activity(user_id)
        streak = gamification.get_streak(user_id)
        assert streak["current_streak"] == 1
        
        # Same day - no change
        gamification.record_daily_activity(user_id)
        streak = gamification.get_streak(user_id)
        assert streak["current_streak"] == 1
        
        # Simulate next day
        gamification._set_last_activity(user_id, datetime.now() - timedelta(days=1))
        gamification.record_daily_activity(user_id)
        streak = gamification.get_streak(user_id)
        assert streak["current_streak"] == 2
    
    def test_streak_multiplier(self, gamification):
        """Test XP multiplier at 7-day streak"""
        user_id = "test_user_multiplier"
        
        # Build up streak
        for i in range(7):
            gamification._set_last_activity(user_id, datetime.now() - timedelta(days=7-i))
            gamification.record_daily_activity(user_id)
        
        # Check streak
        streak = gamification.get_streak(user_id)
        assert streak["current_streak"] == 7
        assert streak["has_multiplier"]
        assert streak["multiplier"] == 1.5
    
    def test_streak_broken(self, gamification):
        """Test streak reset after missing a day"""
        user_id = "test_user_broken"
        
        # Build 3-day streak
        for i in range(3):
            gamification._set_last_activity(user_id, datetime.now() - timedelta(days=3-i))
            gamification.record_daily_activity(user_id)
        
        # Miss 2 days
        gamification._set_last_activity(user_id, datetime.now() - timedelta(days=3))
        gamification.record_daily_activity(user_id)
        
        streak = gamification.get_streak(user_id)
        assert streak["current_streak"] == 1  # Reset
    
    def test_badges(self, gamification):
        """Test badge awarding"""
        user_id = "test_user_badges"
        
        # Award badge
        gamification.award_badge(user_id, "first_steps", "Complete first lesson")
        badges = gamification.get_user_badges(user_id)
        assert len(badges) == 1
        assert badges[0]["id"] == "first_steps"
        
        # Award another badge
        gamification.award_badge(user_id, "week_warrior", "7-day streak")
        badges = gamification.get_user_badges(user_id)
        assert len(badges) == 2
    
    def test_badge_deduplication(self, gamification):
        """Test that badges are not awarded twice"""
        user_id = "test_user_dedup"
        
        # Award same badge twice
        gamification.award_badge(user_id, "first_steps", "Complete first lesson")
        gamification.award_badge(user_id, "first_steps", "Complete first lesson")
        
        badges = gamification.get_user_badges(user_id)
        assert len(badges) == 1
    
    def test_xp_rewards_by_action(self, gamification):
        """Test XP reward amounts for different actions"""
        rewards = gamification.get_xp_rewards()
        
        assert rewards["lesson_complete"] == 50
        assert rewards["quiz_perfect"] == 25
        assert rewards["daily_streak"] == 10
        assert rewards["first_market_query"] == 20
        assert rewards["api_key_added"] == 30
    
    def test_leaderboard_stats(self, gamification):
        """Test user stats for leaderboard"""
        user_id = "test_user_stats"
        
        # Add activity
        gamification.add_xp(user_id, 500, "test")
        gamification.record_daily_activity(user_id)
        gamification.award_badge(user_id, "first_steps", "Test")
        
        stats = gamification.get_user_stats(user_id)
        assert stats["xp"] == 500
        assert stats["level"]["level"] == 5  # Apprentice
        assert stats["streak"]["current_streak"] == 1
        assert stats["badge_count"] == 1
    
    def test_all_level_definitions(self, gamification):
        """Test all 10 level definitions"""
        levels = gamification.get_all_levels()
        
        assert len(levels) == 10
        assert levels[0]["name"] == "Novice"
        assert levels[1]["name"] == "Learner"
        assert levels[9]["name"] == "Legend"
        
        # XP requirements should be increasing
        for i in range(len(levels) - 1):
            assert levels[i+1]["xp_required"] > levels[i]["xp_required"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
