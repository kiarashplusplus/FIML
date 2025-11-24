"""
Integration tests for bot components working together
"""

import pytest
from pathlib import Path
import yaml
from fiml.bot.education.lesson_engine import LessonContentEngine
from fiml.bot.education.quiz_system import QuizSystem
from fiml.bot.education.gamification import GamificationEngine
from fiml.bot.education.compliance_filter import EducationalComplianceFilter


class TestBotIntegration:
    """Test components working together"""
    
    @pytest.fixture
    def bot_components(self, tmp_path):
        """Create all bot components"""
        # Create a real lesson file
        lesson_path = tmp_path / "lessons"
        lesson_path.mkdir()
        
        lesson_data = {
            "id": "integration_test_001",
            "version": "1.0",
            "title": "Integration Test Lesson",
            "difficulty": "beginner",
            "duration_minutes": 5,
            "sections": [
                {
                    "type": "introduction",
                    "content": "Learn about P/E ratios and valuation."
                }
            ],
            "quiz": {
                "questions": [
                    {
                        "type": "multiple_choice",
                        "text": "What does P/E ratio measure?",
                        "options": ["Price vs Earnings", "Profit vs Equity", "Price vs Expenses"],
                        "correct_answer": "Price vs Earnings",
                        "explanation": "P/E = Price per share / Earnings per share",
                        "xp_reward": 10
                    },
                    {
                        "type": "true_false",
                        "text": "A high P/E ratio always means a stock is overvalued.",
                        "correct_answer": "false",
                        "explanation": "High P/E can indicate growth expectations.",
                        "xp_reward": 10
                    }
                ]
            },
            "xp_reward": 50
        }
        
        lesson_file = lesson_path / "integration_test_001.yaml"
        with open(lesson_file, 'w') as f:
            yaml.dump(lesson_data, f)
        
        return {
            "lesson_engine": LessonContentEngine(lessons_dir=str(lesson_path)),
            "quiz_system": QuizSystem(),
            "gamification": GamificationEngine(),
            "compliance": EducationalComplianceFilter()
        }
    
    def test_complete_lesson_flow(self, bot_components):
        """Test complete user flow: lesson -> quiz -> XP"""
        user_id = "integration_user_001"
        lesson_id = "integration_test_001"
        
        lesson_engine = bot_components["lesson_engine"]
        quiz_system = bot_components["quiz_system"]
        gamification = bot_components["gamification"]
        
        # Step 1: Load lesson
        lesson = lesson_engine.load_lesson(lesson_id)
        assert lesson is not None
        
        # Step 2: Mark lesson as started
        lesson_engine.mark_lesson_started(user_id, lesson_id)
        assert lesson_engine.is_lesson_in_progress(user_id, lesson_id)
        
        # Step 3: Complete lesson and award XP
        lesson_engine.mark_lesson_completed(user_id, lesson_id)
        gamification.add_xp(user_id, lesson["xp_reward"], "lesson_complete")
        
        # Verify lesson completion
        assert lesson_engine.is_lesson_completed(user_id, lesson_id)
        assert gamification.get_user_xp(user_id) == 50
        
        # Step 4: Start quiz
        quiz_session = quiz_system.create_session(user_id, lesson_id, lesson["quiz"]["questions"])
        
        # Step 5: Answer questions
        result1 = quiz_system.answer_question(quiz_session, 0, "Price vs Earnings")
        assert result1["correct"]
        gamification.add_xp(user_id, result1["xp_earned"], "quiz_answer")
        
        result2 = quiz_system.answer_question(quiz_session, 1, "false")
        assert result2["correct"]
        gamification.add_xp(user_id, result2["xp_earned"], "quiz_answer")
        
        # Step 6: Check final score
        score = quiz_system.get_quiz_score(quiz_session)
        assert score["percentage"] == 100.0
        
        # Step 7: Award perfect quiz badge
        if score["percentage"] == 100.0:
            gamification.award_badge(user_id, "perfect_score", "100% on quiz")
        
        # Verify final state
        total_xp = gamification.get_user_xp(user_id)
        assert total_xp == 70  # 50 (lesson) + 10 + 10 (quiz)
        
        badges = gamification.get_user_badges(user_id)
        assert len(badges) == 1
        assert badges[0]["id"] == "perfect_score"
    
    def test_compliance_filtering_in_flow(self, bot_components):
        """Test compliance filtering during user interaction"""
        compliance = bot_components["compliance"]
        
        # User asks inappropriate question
        question = "Should I buy AAPL stock?"
        result = compliance.filter_user_question(question)
        
        assert not result.is_allowed
        assert len(result.alternative_suggestions) > 0
        
        # Bot suggests educational alternative
        educational_question = result.alternative_suggestions[0]
        result2 = compliance.filter_user_question(educational_question)
        assert result2.is_allowed
    
    def test_lesson_prerequisites_with_gamification(self, bot_components):
        """Test prerequisite system integrated with XP/levels"""
        user_id = "prereq_user"
        lesson_engine = bot_components["lesson_engine"]
        gamification = bot_components["gamification"]
        
        # Create advanced lesson with prerequisites
        advanced_lesson = {
            "id": "advanced_001",
            "prerequisites": ["integration_test_001"]
        }
        
        # User starts as Novice
        level = gamification.get_user_level(user_id)
        assert level["level"] == 1
        
        # Can't access advanced lesson without prerequisites
        can_access = lesson_engine.can_access_lesson(user_id, advanced_lesson)
        assert not can_access
        
        # Complete prerequisite
        lesson_engine.mark_lesson_completed(user_id, "integration_test_001")
        gamification.add_xp(user_id, 50, "lesson_complete")
        
        # Now can access
        can_access = lesson_engine.can_access_lesson(user_id, advanced_lesson)
        assert can_access
    
    def test_daily_streak_with_lessons(self, bot_components):
        """Test daily streak tracking with lesson completion"""
        user_id = "streak_user"
        lesson_engine = bot_components["lesson_engine"]
        gamification = bot_components["gamification"]
        
        # Complete a lesson
        lesson_engine.mark_lesson_completed(user_id, "integration_test_001")
        gamification.add_xp(user_id, 50, "lesson_complete")
        
        # Record daily activity
        gamification.record_daily_activity(user_id)
        
        streak = gamification.get_streak(user_id)
        assert streak["current_streak"] == 1
        
        # Award first lesson badge
        if not gamification.has_badge(user_id, "first_steps"):
            gamification.award_badge(user_id, "first_steps", "Complete first lesson")
        
        badges = gamification.get_user_badges(user_id)
        assert any(b["id"] == "first_steps" for b in badges)
    
    def test_level_up_notification(self, bot_components):
        """Test detecting when user levels up"""
        user_id = "levelup_user"
        gamification = bot_components["gamification"]
        
        # Start at level 1
        level_before = gamification.get_user_level(user_id)
        assert level_before["level"] == 1
        
        # Add enough XP to level up (100 XP for level 2)
        gamification.add_xp(user_id, 100, "test")
        
        level_after = gamification.get_user_level(user_id)
        assert level_after["level"] == 2
        assert level_after["name"] == "Learner"
        
        # User should see level up notification
        assert level_after["level"] > level_before["level"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
