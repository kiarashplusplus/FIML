import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fiml.bot.core.gateway import UnifiedBotGateway, AbstractMessage, IntentType
from fiml.bot.education.lesson_engine import LessonContentEngine, Lesson, RenderedLesson
from fiml.bot.education.quiz_system import QuizSystem, QuizSession, QuizQuestion

@pytest.fixture
def mock_lesson_engine():
    engine = MagicMock(spec=LessonContentEngine)
    engine.load_lesson = AsyncMock()
    engine.render_lesson = AsyncMock()
    engine.mark_lesson_started = MagicMock()
    engine.get_user_progress = AsyncMock(return_value={"completed": [], "in_progress": []})
    engine.list_lessons = AsyncMock(return_value=[
        {"id": "lesson1", "title": "Lesson 1", "difficulty": "beginner"},
        {"id": "lesson2", "title": "Lesson 2", "difficulty": "intermediate"}
    ])
    engine.create_sample_lesson = MagicMock()
    return engine

@pytest.fixture
def mock_quiz_system():
    system = MagicMock(spec=QuizSystem)
    system.create_session = MagicMock(return_value="session_123")
    system.get_current_question = AsyncMock()
    system.submit_answer = AsyncMock()
    return system

@pytest.fixture
def gateway(mock_lesson_engine, mock_quiz_system):
    # Mock other dependencies
    mock_mentor = MagicMock()
    mock_data_adapter = MagicMock()
    mock_narrative = MagicMock()
    
    gateway = UnifiedBotGateway(
        ai_mentor_service=mock_mentor,
        fiml_data_adapter=mock_data_adapter,
        narrative_generator=mock_narrative
    )
    
    # Inject mocks
    gateway.lesson_engine = mock_lesson_engine
    gateway.quiz_system = mock_quiz_system
    
    return gateway

@pytest.mark.asyncio
async def test_help_command_returns_actions(gateway):
    response = await gateway.handle_message(
        platform="mobile_app",
        user_id="user123",
        text="/help"
    )
    
    assert "FIML Educational Bot Commands" in response.text
    assert response.actions is not None
    assert len(response.actions) > 0
    assert any(a["action"] == "/lesson" for a in response.actions)

@pytest.mark.asyncio
async def test_lesson_command_returns_list(gateway):
    response = await gateway.handle_message(
        platform="mobile_app",
        user_id="user123",
        text="/lesson"
    )
    
    assert "Available Lessons" in response.text
    assert response.actions is not None
    assert len(response.actions) > 0
    assert any(a["action"].startswith("lesson:start:") for a in response.actions)

@pytest.mark.asyncio
async def test_lesson_start_action(gateway, mock_lesson_engine):
    # Setup mock lesson
    mock_lesson = MagicMock(spec=Lesson)
    mock_lesson_engine.load_lesson.return_value = mock_lesson
    mock_lesson_engine.render_lesson.return_value = RenderedLesson(
        title="Test Lesson",
        content="Lesson Content",
        metadata={}
    )
    
    # Test context-based action
    response = await gateway.handle_message(
        platform="mobile_app",
        user_id="user123",
        text="Start Lesson",
        context={"action": "lesson:start:stock_basics_001"}
    )
    
    assert response.text == "Lesson Content"
    assert response.actions is not None
    assert any(a["action"].startswith("quiz:start:") for a in response.actions)
    
    # Verify engine calls
    mock_lesson_engine.load_lesson.assert_called_with("stock_basics_001")
    mock_lesson_engine.mark_lesson_started.assert_called_with("user123", "stock_basics_001")

@pytest.mark.asyncio
async def test_quiz_start_action(gateway, mock_lesson_engine, mock_quiz_system):
    # Setup mock lesson and quiz
    mock_lesson = MagicMock(spec=Lesson)
    mock_lesson.title = "Test Lesson"
    mock_lesson.quiz_questions = [MagicMock()]
    mock_lesson_engine.load_lesson.return_value = mock_lesson
    
    mock_question = QuizQuestion(
        id="q1",
        type="multiple_choice",
        text="Question 1",
        options=[{"text": "A"}, {"text": "B"}]
    )
    mock_quiz_system.get_current_question.return_value = mock_question
    
    # Test context-based action
    response = await gateway.handle_message(
        platform="mobile_app",
        user_id="user123",
        text="Take Quiz",
        context={"action": "quiz:start:stock_basics_001"}
    )
    
    assert "Question 1" in response.text
    assert response.actions is not None
    assert len(response.actions) == 2 # 2 options
    assert response.actions[0]["text"] == "A"

@pytest.mark.asyncio
async def test_quiz_answer_action(gateway, mock_quiz_system):
    # Setup mock answer result
    mock_quiz_system.submit_answer.return_value = {
        "correct": True,
        "explanation": "Good job",
        "xp_earned": 10,
        "quiz_complete": False,
        "score": 1,
        "total_questions": 2
    }
    
    mock_next_question = QuizQuestion(
        id="q2",
        type="true_false",
        text="Question 2",
        options=[]
    )
    mock_quiz_system.get_current_question.return_value = mock_next_question
    
    # Test context-based action
    response = await gateway.handle_message(
        platform="mobile_app",
        user_id="user123",
        text="A",
        context={"action": "quiz:answer:session_123:0:A"}
    )
    
    assert "Correct!" in response.text
    assert "Question 2" in response.text
    assert response.actions is not None
    assert len(response.actions) == 2 # True/False options
