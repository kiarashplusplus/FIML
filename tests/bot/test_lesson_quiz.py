"""
Tests for LessonContentEngine (Component 6) and QuizSystem (Component 7)
"""


from datetime import datetime, timedelta

import pytest
import yaml

from fiml.bot.education.lesson_engine import LessonContentEngine
from fiml.bot.education.quiz_system import QuizSystem


class TestLessonContentEngine:
    """Test lesson loading and rendering"""

    @pytest.fixture
    def lesson_engine(self):
        """Create a lesson engine"""
        return LessonContentEngine()

    @pytest.fixture
    def sample_lesson_path(self, tmp_path):
        """Create a sample lesson YAML"""
        lesson_data = {
            "id": "test_lesson_001",
            "version": "1.0",
            "title": "Test Lesson",
            "difficulty": "beginner",
            "duration_minutes": 5,
            "sections": [
                {
                    "type": "introduction",
                    "content": "This is a test lesson."
                }
            ],
            "quiz": {
                "questions": [
                    {
                        "type": "multiple_choice",
                        "text": "What is 2+2?",
                        "options": ["3", "4", "5"],
                        "correct_answer": "4",
                        "explanation": "2+2 equals 4"
                    }
                ]
            },
            "xp_reward": 50
        }

        lesson_file = tmp_path / "test_lesson_001.yaml"
        with open(lesson_file, 'w') as f:
            yaml.dump(lesson_data, f)

        return lesson_file

    async def test_load_lesson(self, lesson_engine, sample_lesson_path):
        """Test loading a lesson from YAML"""
        lesson = lesson_engine.load_lesson_from_file(str(sample_lesson_path))
        assert lesson is not None
        assert lesson["id"] == "test_lesson_001"
        assert lesson["title"] == "Test Lesson"
        assert lesson["xp_reward"] == 50

    async def test_lesson_validation(self, lesson_engine, sample_lesson_path):
        """Test lesson structure validation"""
        lesson = lesson_engine.load_lesson_from_file(str(sample_lesson_path))
        is_valid = lesson_engine.validate_lesson(lesson)
        assert is_valid

    async def test_render_lesson(self, lesson_engine, sample_lesson_path):
        """Test rendering lesson content"""
        lesson = lesson_engine.load_lesson_from_file(str(sample_lesson_path))
        rendered = await lesson_engine.render_lesson(lesson, user_id="test_user")

        assert "Test Lesson" in rendered
        assert "This is a test lesson" in rendered

    async def test_track_progress(self, lesson_engine):
        """Test lesson progress tracking"""
        user_id = "test_user_progress"
        lesson_id = "test_lesson_001"

        # Mark as started
        lesson_engine.mark_lesson_started(user_id, lesson_id)
        assert lesson_engine.is_lesson_in_progress(user_id, lesson_id)

        # Mark as completed
        lesson_engine.mark_lesson_completed(user_id, lesson_id)
        assert lesson_engine.is_lesson_completed(user_id, lesson_id)
        assert not lesson_engine.is_lesson_in_progress(user_id, lesson_id)

    async def test_prerequisites(self, lesson_engine):
        """Test prerequisite checking"""
        user_id = "test_user_prereq"

        # Lesson with prerequisites
        lesson = {
            "id": "advanced_lesson",
            "prerequisites": ["basic_lesson_001"]
        }

        # Should not be available without prerequisites
        can_access = lesson_engine.can_access_lesson(user_id, lesson)
        assert not can_access

        # Complete prerequisite
        lesson_engine.mark_lesson_completed(user_id, "basic_lesson_001")

        # Should now be available
        can_access = lesson_engine.can_access_lesson(user_id, lesson)
        assert can_access


class TestQuizSystem:
    """Test quiz functionality"""

    @pytest.fixture
    def quiz_system(self):
        """Create a quiz system"""
        return QuizSystem()

    async def test_create_quiz_session(self, quiz_system):
        """Test creating a quiz session"""
        user_id = "test_user_quiz"
        lesson_id = "test_lesson_001"
        questions = [
            {
                "type": "multiple_choice",
                "text": "What is 2+2?",
                "options": ["3", "4", "5"],
                "correct_answer": "4"
            }
        ]

        session_id = quiz_system.create_session(user_id, lesson_id, questions)
        assert session_id is not None

        # Get session
        session = quiz_system.get_session(session_id)
        assert session is not None
        assert session["user_id"] == user_id
        assert len(session["questions"]) == 1

    async def test_answer_question_correct(self, quiz_system):
        """Test answering a question correctly"""
        user_id = "test_user_answer"
        questions = [
            {
                "type": "multiple_choice",
                "text": "What is 2+2?",
                "options": ["3", "4", "5"],
                "correct_answer": "4",
                "explanation": "2+2 equals 4",
                "xp_reward": 10
            }
        ]

        session_id = quiz_system.create_session(user_id, "lesson_001", questions)

        # Answer correctly
        result = quiz_system.answer_question(session_id, 0, "4")
        assert result["correct"]
        assert result["xp_earned"] == 10
        assert "2+2 equals 4" in result["explanation"]

    async def test_answer_question_incorrect(self, quiz_system):
        """Test answering a question incorrectly"""
        user_id = "test_user_wrong"
        questions = [
            {
                "type": "multiple_choice",
                "text": "What is 2+2?",
                "options": ["3", "4", "5"],
                "correct_answer": "4",
                "explanation": "2+2 equals 4"
            }
        ]

        session_id = quiz_system.create_session(user_id, "lesson_001", questions)

        # Answer incorrectly
        result = quiz_system.answer_question(session_id, 0, "3")
        assert not result["correct"]
        assert result["xp_earned"] == 0
        assert "explanation" in result

    async def test_calculate_quiz_score(self, quiz_system):
        """Test quiz score calculation"""
        user_id = "test_user_score"
        questions = [
            {
                "type": "multiple_choice",
                "text": "Q1",
                "correct_answer": "A",
                "xp_reward": 10
            },
            {
                "type": "multiple_choice",
                "text": "Q2",
                "correct_answer": "B",
                "xp_reward": 10
            },
            {
                "type": "multiple_choice",
                "text": "Q3",
                "correct_answer": "C",
                "xp_reward": 10
            }
        ]

        session_id = quiz_system.create_session(user_id, "lesson_001", questions)

        # Answer 2 out of 3 correctly
        quiz_system.answer_question(session_id, 0, "A")  # Correct
        quiz_system.answer_question(session_id, 1, "X")  # Incorrect
        quiz_system.answer_question(session_id, 2, "C")  # Correct

        # Get score
        score = quiz_system.get_quiz_score(session_id)
        assert score["total_questions"] == 3
        assert score["correct_answers"] == 2
        assert score["percentage"] == pytest.approx(66.67, 0.1)
        assert score["total_xp"] == 20

    async def test_true_false_question(self, quiz_system):
        """Test true/false question type"""
        user_id = "test_user_tf"
        questions = [
            {
                "type": "true_false",
                "text": "The sky is blue.",
                "correct_answer": "true"
            }
        ]

        session_id = quiz_system.create_session(user_id, "lesson_001", questions)

        # Answer correctly
        result = quiz_system.answer_question(session_id, 0, "true")
        assert result["correct"]

        # Answer incorrectly
        session_id2 = quiz_system.create_session(user_id, "lesson_002", questions)
        result2 = quiz_system.answer_question(session_id2, 0, "false")
        assert not result2["correct"]

    async def test_numeric_question(self, quiz_system):
        """Test numeric question type with tolerance"""
        user_id = "test_user_numeric"
        questions = [
            {
                "type": "numeric",
                "text": "What is 10% of 100?",
                "correct_answer": 10.0,
                "tolerance": 0.1
            }
        ]

        session_id = quiz_system.create_session(user_id, "lesson_001", questions)

        # Exact answer
        result1 = quiz_system.answer_question(session_id, 0, "10.0")
        assert result1["correct"]

        # Within tolerance
        session_id2 = quiz_system.create_session(user_id, "lesson_002", questions)
        result2 = quiz_system.answer_question(session_id2, 0, "10.05")
        assert result2["correct"]

        # Outside tolerance
        session_id3 = quiz_system.create_session(user_id, "lesson_003", questions)
        result3 = quiz_system.answer_question(session_id3, 0, "15.0")
        assert not result3["correct"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
