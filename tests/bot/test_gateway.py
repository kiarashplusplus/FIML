"""
Tests for UnifiedBotGateway (Component 3)
Tests message routing and intent classification
"""
import pytest
from fiml.bot.core.gateway import (
    UnifiedBotGateway,
    AbstractMessage,
    AbstractResponse,
    IntentType
)


class TestUnifiedBotGateway:
    """Test suite for bot gateway"""
    
    def test_init_gateway(self):
        """Test gateway initialization"""
        gateway = UnifiedBotGateway()
        assert gateway is not None
    
    def test_classify_command_intent(self):
        """Test classification of bot commands"""
        gateway = UnifiedBotGateway()
        
        # Test command messages
        intent = gateway.classify_intent("/start")
        assert intent == IntentType.COMMAND
        
        intent = gateway.classify_intent("/help")
        assert intent == IntentType.COMMAND
        
        intent = gateway.classify_intent("/lesson")
        assert intent == IntentType.COMMAND
    
    def test_classify_lesson_request(self):
        """Test classification of lesson requests"""
        gateway = UnifiedBotGateway()
        
        intent = gateway.classify_intent("I want to learn about stocks")
        assert intent in [IntentType.LESSON_REQUEST, IntentType.AI_QUESTION]
        
        intent = gateway.classify_intent("teach me about P/E ratio")
        assert intent in [IntentType.LESSON_REQUEST, IntentType.AI_QUESTION]
    
    def test_classify_quiz_answer(self):
        """Test classification of quiz answers in quiz context"""
        gateway = UnifiedBotGateway()
        
        # Set session state to quiz
        session_state = {'in_quiz': True}
        intent = gateway.classify_intent("A", session_state=session_state)
        assert intent == IntentType.QUIZ_ANSWER
        
        intent = gateway.classify_intent("42", session_state=session_state)
        assert intent == IntentType.QUIZ_ANSWER
    
    def test_classify_ai_question(self):
        """Test classification of questions for AI mentor"""
        gateway = UnifiedBotGateway()
        
        intent = gateway.classify_intent("What is a stock?")
        assert intent in [IntentType.AI_QUESTION, IntentType.LESSON_REQUEST]
        
        intent = gateway.classify_intent("Can you explain diversification?")
        assert intent in [IntentType.AI_QUESTION, IntentType.LESSON_REQUEST]
    
    def test_classify_market_query(self):
        """Test classification of market data queries"""
        gateway = UnifiedBotGateway()
        
        intent = gateway.classify_intent("What is AAPL price?")
        assert intent in [IntentType.MARKET_QUERY, IntentType.AI_QUESTION]
        
        intent = gateway.classify_intent("Show me TSLA stock")
        assert intent in [IntentType.MARKET_QUERY, IntentType.AI_QUESTION]
    
    def test_classify_navigation(self):
        """Test classification of navigation commands"""
        gateway = UnifiedBotGateway()
        
        intent = gateway.classify_intent("back")
        assert intent == IntentType.NAVIGATION
        
        intent = gateway.classify_intent("menu")
        assert intent == IntentType.NAVIGATION
        
        intent = gateway.classify_intent("next")
        assert intent == IntentType.NAVIGATION
    
    def test_session_state_management(self):
        """Test session state tracking"""
        gateway = UnifiedBotGateway()
        
        # Create session
        session = gateway.create_session("user_123")
        assert session is not None
        assert session.user_id == "user_123"
        assert session.state == {}
    
    def test_update_session_state(self):
        """Test updating session state"""
        gateway = UnifiedBotGateway()
        
        session = gateway.create_session("user_123")
        gateway.update_session_state("user_123", {'in_lesson': True, 'lesson_id': 'stock_basics_001'})
        
        updated_session = gateway.get_session("user_123")
        assert updated_session.state.get('in_lesson') is True
        assert updated_session.state.get('lesson_id') == 'stock_basics_001'
    
    def test_context_aware_classification(self):
        """Test that context affects intent classification"""
        gateway = UnifiedBotGateway()
        
        # Same text, different context
        quiz_context = {'in_quiz': True}
        lesson_context = {'in_lesson': True}
        
        intent_quiz = gateway.classify_intent("A", session_state=quiz_context)
        intent_lesson = gateway.classify_intent("A", session_state=lesson_context)
        
        # In quiz context, should be quiz answer
        assert intent_quiz == IntentType.QUIZ_ANSWER
    
    def test_route_message_to_handler(self):
        """Test message routing to appropriate handler"""
        gateway = UnifiedBotGateway()
        
        # Register a test handler
        def test_handler(message):
            return AbstractResponse(text="Test response")
        
        gateway.register_handler(IntentType.COMMAND, test_handler)
        
        # Route a command
        response = gateway.route_message("/help")
        assert response is not None
    
    def test_abstract_message_creation(self):
        """Test creating platform-agnostic messages"""
        message = AbstractMessage(
            text="Hello",
            user_id="user_123",
            platform="telegram"
        )
        
        assert message.text == "Hello"
        assert message.user_id == "user_123"
        assert message.platform == "telegram"
    
    def test_abstract_response_creation(self):
        """Test creating platform-agnostic responses"""
        response = AbstractResponse(
            text="Response text",
            buttons=[{"text": "Button 1", "data": "action_1"}]
        )
        
        assert response.text == "Response text"
        assert len(response.buttons) == 1
        assert response.buttons[0]["text"] == "Button 1"
    
    def test_multiple_session_isolation(self):
        """Test that multiple user sessions are isolated"""
        gateway = UnifiedBotGateway()
        
        session1 = gateway.create_session("user_123")
        session2 = gateway.create_session("user_456")
        
        gateway.update_session_state("user_123", {'score': 100})
        gateway.update_session_state("user_456", {'score': 200})
        
        s1 = gateway.get_session("user_123")
        s2 = gateway.get_session("user_456")
        
        assert s1.state['score'] == 100
        assert s2.state['score'] == 200
    
    def test_session_cleanup(self):
        """Test session cleanup"""
        gateway = UnifiedBotGateway()
        
        session = gateway.create_session("user_123")
        assert gateway.get_session("user_123") is not None
        
        gateway.cleanup_session("user_123")
        # After cleanup, session should be gone or reset
        cleaned = gateway.get_session("user_123")
        assert cleaned is None or cleaned.state == {}
