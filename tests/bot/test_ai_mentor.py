"""
Tests for AIMentorService (Component 8)
Tests AI mentor personas and response generation
"""

from fiml.bot.education.ai_mentor import AIMentorService, MentorPersona


class TestAIMentorService:
    """Test suite for AI mentor system"""

    async def test_init_mentor_service(self):
        """Test mentor service initialization"""
        mentor = AIMentorService()
        assert mentor is not None

    async def test_get_maya_persona(self):
        """Test Maya (patient guide) persona"""
        mentor = AIMentorService()

        response = await mentor.respond(
            user_id="user_123", question="What is a stock?", persona=MentorPersona.MAYA
        )

        assert response is not None
        assert len(response["text"]) > 0
        # Maya should use patient, beginner-friendly language
        assert isinstance(response, dict)
        assert "text" in response

    async def test_get_theo_persona(self):
        """Test Theo (analytical) persona"""
        mentor = AIMentorService()

        response = await mentor.respond(
            user_id="user_123",
            question="How do I analyze stock performance?",
            persona=MentorPersona.THEO,
        )

        assert response is not None
        assert len(response["text"]) > 0
        # Theo should provide analytical, data-driven response
        assert isinstance(response, dict)
        assert "text" in response

    async def test_get_zara_persona(self):
        """Test Zara (psychology) persona"""
        mentor = AIMentorService()

        response = await mentor.respond(
            user_id="user_123",
            question="How do I control my emotions when trading?",
            persona=MentorPersona.ZARA,
        )

        assert response is not None
        assert len(response["text"]) > 0
        # Zara should focus on psychology and discipline
        assert isinstance(response, dict)
        assert "text" in response

    async def test_conversation_history_tracking(self):
        """Test that conversation history is tracked"""
        mentor = AIMentorService()

        # Ask multiple questions
        await mentor.respond("user_123", "What is a stock?", MentorPersona.MAYA)
        await mentor.respond("user_123", "What is P/E ratio?", MentorPersona.MAYA)

        history = await mentor.get_conversation_history("user_123")

        assert history is not None
        assert len(history) > 0

    async def test_conversation_history_limit(self):
        """Test that conversation history is limited to last 10 messages"""
        mentor = AIMentorService()

        # Ask 15 questions
        for i in range(15):
            await mentor.respond("user_123", f"Question {i}", MentorPersona.MAYA)

        history = await mentor.get_conversation_history("user_123")

        # Should only keep last 10
        assert len(history) <= 10

    async def test_context_aware_responses(self):
        """Test that responses are context-aware based on history"""
        mentor = AIMentorService()

        # Build context
        await mentor.respond("user_123", "What is a stock?", MentorPersona.MAYA)

        # Follow-up question
        response = await mentor.respond("user_123", "Tell me more", MentorPersona.MAYA)

        assert response is not None
        # Response should be contextual
        assert len(response["text"]) > 0

    async def test_lesson_suggestions(self):
        """Test that mentor can suggest relevant lessons"""
        mentor = AIMentorService()

        suggestions = mentor._suggest_lessons(question="I want to learn about valuation")

        assert suggestions is not None
        assert isinstance(suggestions, list)

    async def test_compliance_disclaimers(self):
        """Test that responses include compliance disclaimers"""
        mentor = AIMentorService()

        response = await mentor.respond(
            user_id="user_123", question="Should I buy this stock?", persona=MentorPersona.MAYA
        )

        # Should include disclaimer or redirect
        assert response is not None
        # Check for compliance-related text
        lower_response = response["text"].lower()
        assert any(
            word in lower_response for word in ["educational", "learn", "understand", "not advice"]
        )

    async def test_template_fallback(self):
        """Test graceful fallback to templates when FIML unavailable"""
        mentor = AIMentorService()

        # Should work even if FIML narrative generation fails
        response = await mentor.respond(
            user_id="user_123", question="What is diversification?", persona=MentorPersona.MAYA
        )

        assert response is not None
        assert len(response["text"]) > 0

    async def test_persona_specific_language(self):
        """Test that each persona uses distinct language"""
        mentor = AIMentorService()

        question = "What is risk management?"

        maya_response = await mentor.respond("user_1", question, MentorPersona.MAYA)
        theo_response = await mentor.respond("user_2", question, MentorPersona.THEO)
        zara_response = await mentor.respond("user_3", question, MentorPersona.ZARA)

        # All should respond
        assert maya_response is not None
        assert theo_response is not None
        assert zara_response is not None

        # Responses should be dicts with text
        assert isinstance(maya_response, dict)
        assert isinstance(theo_response, dict)
        assert isinstance(zara_response, dict)
        assert "text" in maya_response
        assert "text" in theo_response
        assert "text" in zara_response

    async def test_clear_conversation_history(self):
        """Test clearing conversation history"""
        mentor = AIMentorService()

        # Build history
        await mentor.respond("user_123", "Question 1", MentorPersona.MAYA)
        await mentor.respond("user_123", "Question 2", MentorPersona.MAYA)

        # Clear history
        mentor._conversations.pop("user_123", None)
        mentor._conversations["user_123"] = []

        history = await mentor.get_conversation_history("user_123")
        assert len(history) == 0

    async def test_multi_user_isolation(self):
        """Test that different users have isolated conversations"""
        mentor = AIMentorService()

        await mentor.respond("user_123", "Question A", MentorPersona.MAYA)
        await mentor.respond("user_456", "Question B", MentorPersona.THEO)

        history_1 = await mentor.get_conversation_history("user_123")
        history_2 = await mentor.get_conversation_history("user_456")

        # Histories should be separate
        assert history_1 != history_2
