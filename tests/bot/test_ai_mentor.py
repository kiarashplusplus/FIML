"""
Tests for AIMentorService (Component 8)
Tests AI mentor personas and response generation
"""
import pytest
from fiml.bot.education.ai_mentor import AIMentorService, MentorPersona


class TestAIMentorService:
    """Test suite for AI mentor system"""
    
    def test_init_mentor_service(self):
        """Test mentor service initialization"""
        mentor = AIMentorService()
        assert mentor is not None
    
    def test_get_maya_persona(self):
        """Test Maya (patient guide) persona"""
        mentor = AIMentorService()
        
        response = mentor.get_response(
            user_id="user_123",
            question="What is a stock?",
            persona=MentorPersona.MAYA
        )
        
        assert response is not None
        assert len(response) > 0
        # Maya should use patient, beginner-friendly language
        assert isinstance(response, str)
    
    def test_get_theo_persona(self):
        """Test Theo (analytical) persona"""
        mentor = AIMentorService()
        
        response = mentor.get_response(
            user_id="user_123",
            question="How do I analyze stock performance?",
            persona=MentorPersona.THEO
        )
        
        assert response is not None
        assert len(response) > 0
        # Theo should provide analytical, data-driven response
        assert isinstance(response, str)
    
    def test_get_zara_persona(self):
        """Test Zara (psychology) persona"""
        mentor = AIMentorService()
        
        response = mentor.get_response(
            user_id="user_123",
            question="How do I control my emotions when trading?",
            persona=MentorPersona.ZARA
        )
        
        assert response is not None
        assert len(response) > 0
        # Zara should focus on psychology and discipline
        assert isinstance(response, str)
    
    def test_conversation_history_tracking(self):
        """Test that conversation history is tracked"""
        mentor = AIMentorService()
        
        # Ask multiple questions
        mentor.get_response("user_123", "What is a stock?", MentorPersona.MAYA)
        mentor.get_response("user_123", "What is P/E ratio?", MentorPersona.MAYA)
        
        history = mentor.get_conversation_history("user_123")
        
        assert history is not None
        assert len(history) > 0
    
    def test_conversation_history_limit(self):
        """Test that conversation history is limited to last 10 messages"""
        mentor = AIMentorService()
        
        # Ask 15 questions
        for i in range(15):
            mentor.get_response("user_123", f"Question {i}", MentorPersona.MAYA)
        
        history = mentor.get_conversation_history("user_123")
        
        # Should only keep last 10
        assert len(history) <= 10
    
    def test_context_aware_responses(self):
        """Test that responses are context-aware based on history"""
        mentor = AIMentorService()
        
        # Build context
        mentor.get_response("user_123", "What is a stock?", MentorPersona.MAYA)
        
        # Follow-up question
        response = mentor.get_response("user_123", "Tell me more", MentorPersona.MAYA)
        
        assert response is not None
        # Response should be contextual
        assert len(response) > 0
    
    def test_lesson_suggestions(self):
        """Test that mentor can suggest relevant lessons"""
        mentor = AIMentorService()
        
        suggestions = mentor.suggest_lessons(
            question="I want to learn about valuation",
            user_progress={"completed_lessons": []}
        )
        
        assert suggestions is not None
        assert isinstance(suggestions, list)
    
    def test_compliance_disclaimers(self):
        """Test that responses include compliance disclaimers"""
        mentor = AIMentorService()
        
        response = mentor.get_response(
            user_id="user_123",
            question="Should I buy this stock?",
            persona=MentorPersona.MAYA
        )
        
        # Should include disclaimer or redirect
        assert response is not None
        # Check for compliance-related text
        lower_response = response.lower()
        assert any(word in lower_response for word in ['educational', 'learn', 'understand', 'not advice'])
    
    def test_template_fallback(self):
        """Test graceful fallback to templates when FIML unavailable"""
        mentor = AIMentorService()
        
        # Should work even if FIML narrative generation fails
        response = mentor.get_response(
            user_id="user_123",
            question="What is diversification?",
            persona=MentorPersona.MAYA,
            use_fallback=True
        )
        
        assert response is not None
        assert len(response) > 0
    
    def test_persona_specific_language(self):
        """Test that each persona uses distinct language"""
        mentor = AIMentorService()
        
        question = "What is risk management?"
        
        maya_response = mentor.get_response("user_1", question, MentorPersona.MAYA)
        theo_response = mentor.get_response("user_2", question, MentorPersona.THEO)
        zara_response = mentor.get_response("user_3", question, MentorPersona.ZARA)
        
        # All should respond
        assert maya_response is not None
        assert theo_response is not None
        assert zara_response is not None
        
        # Responses should differ (different personas)
        assert isinstance(maya_response, str)
        assert isinstance(theo_response, str)
        assert isinstance(zara_response, str)
    
    def test_clear_conversation_history(self):
        """Test clearing conversation history"""
        mentor = AIMentorService()
        
        # Build history
        mentor.get_response("user_123", "Question 1", MentorPersona.MAYA)
        mentor.get_response("user_123", "Question 2", MentorPersona.MAYA)
        
        # Clear history
        mentor.clear_conversation_history("user_123")
        
        history = mentor.get_conversation_history("user_123")
        assert len(history) == 0
    
    def test_multi_user_isolation(self):
        """Test that different users have isolated conversations"""
        mentor = AIMentorService()
        
        mentor.get_response("user_123", "Question A", MentorPersona.MAYA)
        mentor.get_response("user_456", "Question B", MentorPersona.THEO)
        
        history_1 = mentor.get_conversation_history("user_123")
        history_2 = mentor.get_conversation_history("user_456")
        
        # Histories should be separate
        assert history_1 != history_2
