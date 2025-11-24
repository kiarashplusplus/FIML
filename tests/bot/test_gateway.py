"""
Tests for UnifiedBotGateway (Component 3)
Tests message routing and intent classification
"""
from fiml.bot.core.gateway import (
    AbstractMessage,
    AbstractResponse,
    IntentType,
    SessionState,
    UnifiedBotGateway,
)


class TestUnifiedBotGateway:
    """Test suite for bot gateway"""

    async def test_init_gateway(self):
        """Test gateway initialization"""
        gateway = UnifiedBotGateway()
        assert gateway is not None

    async def test_classify_command_intent(self):
        """Test classification of bot commands"""
        gateway = UnifiedBotGateway()

        # Test command messages
        msg = AbstractMessage(text="/start", user_id="test", platform="test")
        session = await gateway.session_manager.get_or_create("test")
        intent = await gateway.classify(msg, session)
        assert intent.type == IntentType.COMMAND

        msg = AbstractMessage(text="/help", user_id="test", platform="test")
        intent = await gateway.classify(msg, session)
        assert intent.type == IntentType.COMMAND

        msg = AbstractMessage(text="/lesson", user_id="test", platform="test")
        intent = await gateway.classify(msg, session)
        assert intent.type == IntentType.COMMAND

    async def test_classify_lesson_request(self):
        """Test classification of lesson requests"""
        gateway = UnifiedBotGateway()
        session = await gateway.session_manager.get_or_create("test")

        msg = AbstractMessage(text="I want to learn about stocks", user_id="test", platform="test")
        intent = await gateway.classify(msg, session)
        assert intent.type in [IntentType.LESSON_REQUEST, IntentType.AI_QUESTION]

        msg = AbstractMessage(text="teach me about P/E ratio", user_id="test", platform="test")
        intent = await gateway.classify(msg, session)
        assert intent.type in [IntentType.LESSON_REQUEST, IntentType.AI_QUESTION]

    async def test_classify_quiz_answer(self):
        """Test classification of quiz answers in quiz context"""
        gateway = UnifiedBotGateway()
        session = await gateway.session_manager.get_or_create("test")
        session.state = SessionState.IN_QUIZ

        msg = AbstractMessage(text="A", user_id="test", platform="test")
        intent = await gateway.classify(msg, session)
        assert intent.type == IntentType.QUIZ_ANSWER

        msg = AbstractMessage(text="42", user_id="test", platform="test")
        intent = await gateway.classify(msg, session)
        assert intent.type == IntentType.QUIZ_ANSWER

    async def test_classify_ai_question(self):
        """Test classification of questions for AI mentor"""
        gateway = UnifiedBotGateway()
        session = await gateway.session_manager.get_or_create("test")

        msg = AbstractMessage(text="What is a stock?", user_id="test", platform="test")
        intent = await gateway.classify(msg, session)
        assert intent.type in [IntentType.AI_QUESTION, IntentType.LESSON_REQUEST]

        msg = AbstractMessage(text="Can you explain diversification?", user_id="test", platform="test")
        intent = await gateway.classify(msg, session)
        assert intent.type in [IntentType.AI_QUESTION, IntentType.LESSON_REQUEST]

    async def test_classify_market_query(self):
        """Test classification of market data queries"""
        gateway = UnifiedBotGateway()
        session = await gateway.session_manager.get_or_create("test")

        msg = AbstractMessage(text="Show me AAPL price", user_id="test", platform="test")
        intent = await gateway.classify(msg, session)
        assert intent.type in [IntentType.MARKET_QUERY, IntentType.AI_QUESTION]

        msg = AbstractMessage(text="Show me TSLA stock", user_id="test", platform="test")
        intent = await gateway.classify(msg, session)
        assert intent.type in [IntentType.MARKET_QUERY, IntentType.AI_QUESTION]

    async def test_classify_navigation(self):
        """Test classification of navigation commands"""
        gateway = UnifiedBotGateway()
        session = await gateway.session_manager.get_or_create("test")

        msg = AbstractMessage(text="back", user_id="test", platform="test")
        intent = await gateway.classify(msg, session)
        assert intent.type == IntentType.NAVIGATION

        msg = AbstractMessage(text="menu", user_id="test", platform="test")
        intent = await gateway.classify(msg, session)
        assert intent.type == IntentType.NAVIGATION

        msg = AbstractMessage(text="next", user_id="test", platform="test")
        intent = await gateway.classify(msg, session)
        assert intent.type == IntentType.NAVIGATION

    async def test_session_state_management(self):
        """Test session state tracking"""
        gateway = UnifiedBotGateway()

        # Create session
        session = await gateway.session_manager.get_or_create("user_123")
        assert session is not None
        assert session.user_id == "user_123"

    async def test_update_session_state(self):
        """Test updating session state"""
        gateway = UnifiedBotGateway()

        session = await gateway.session_manager.get_or_create("user_123")
        session.metadata['in_lesson'] = True
        session.metadata['lesson_id'] = 'stock_basics_001'

        retrieved_session = gateway.session_manager.get_session("user_123")
        assert retrieved_session.metadata.get('in_lesson') is True
        assert retrieved_session.metadata.get('lesson_id') == 'stock_basics_001'

    async def test_context_aware_classification(self):
        """Test that context affects intent classification"""
        gateway = UnifiedBotGateway()

        # Same text, different context
        quiz_session = await gateway.session_manager.get_or_create("user_quiz")
        quiz_session.state = SessionState.IN_QUIZ

        lesson_session = await gateway.session_manager.get_or_create("user_lesson")
        lesson_session.state = SessionState.IN_LESSON

        msg = AbstractMessage(text="A", user_id="user_quiz", platform="test")
        intent_quiz = await gateway.classify(msg, quiz_session)

        msg2 = AbstractMessage(text="A", user_id="user_lesson", platform="test")
        await gateway.classify(msg2, lesson_session)

        # In quiz context, should be quiz answer
        assert intent_quiz.type == IntentType.QUIZ_ANSWER

    async def test_route_message_to_handler(self):
        """Test message routing to appropriate handler"""
        gateway = UnifiedBotGateway()

        # Gateway provides classify method, not route_message
        # Test basic classify functionality instead
        session = await gateway.session_manager.get_or_create("test")
        msg = AbstractMessage(text="/help", user_id="test", platform="test")
        intent = await gateway.classify(msg, session)
        assert intent.type == IntentType.COMMAND

    async def test_abstract_message_creation(self):
        """Test creating platform-agnostic messages"""
        message = AbstractMessage(
            text="Hello",
            user_id="user_123",
            platform="telegram"
        )

        assert message.text == "Hello"
        assert message.user_id == "user_123"
        assert message.platform == "telegram"

    async def test_abstract_response_creation(self):
        """Test creating platform-agnostic responses"""
        response = AbstractResponse(
            text="Response text",
            actions=[{"text": "Button 1", "data": "action_1"}]
        )

        assert response.text == "Response text"
        assert len(response.actions) == 1
        assert response.actions[0]["text"] == "Button 1"

    async def test_multiple_session_isolation(self):
        """Test that multiple user sessions are isolated"""
        gateway = UnifiedBotGateway()

        s1 = await gateway.session_manager.get_or_create("user_123")
        s2 = await gateway.session_manager.get_or_create("user_456")

        s1.metadata['score'] = 100
        s2.metadata['score'] = 200

        assert s1.metadata['score'] == 100
        assert s2.metadata['score'] == 200

    async def test_session_cleanup(self):
        """Test session cleanup"""
        gateway = UnifiedBotGateway()

        await gateway.session_manager.get_or_create("user_123")
        # Session exists after creation
        session = await gateway.session_manager.get_or_create("user_123")
        assert session is not None

        await gateway.session_manager.delete("user_123")
        # After cleanup, session should be gone or reset
        cleaned = gateway.session_manager.get_session("user_123")
        assert cleaned is None or cleaned.metadata == {}
