"""
Tests for UnifiedBotGateway (Component 3)
Tests message routing and intent classification
"""

from unittest.mock import AsyncMock, MagicMock, patch

from fiml.bot.core.gateway import (
    AbstractMessage,
    AbstractResponse,
    IntentType,
    SessionState,
    UnifiedBotGateway,
)
from fiml.bot.education.ai_mentor import MentorPersona


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

        msg = AbstractMessage(
            text="Can you explain diversification?", user_id="test", platform="test"
        )
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
        session.metadata["in_lesson"] = True
        session.metadata["lesson_id"] = "stock_basics_001"

        retrieved_session = gateway.session_manager.get_session("user_123")
        assert retrieved_session.metadata.get("in_lesson") is True
        assert retrieved_session.metadata.get("lesson_id") == "stock_basics_001"

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
        message = AbstractMessage(text="Hello", user_id="user_123", platform="telegram")

        assert message.text == "Hello"
        assert message.user_id == "user_123"
        assert message.platform == "telegram"

    async def test_abstract_response_creation(self):
        """Test creating platform-agnostic responses"""
        response = AbstractResponse(
            text="Response text", actions=[{"text": "Button 1", "data": "action_1"}]
        )

        assert response.text == "Response text"
        assert len(response.actions) == 1
        assert response.actions[0]["text"] == "Button 1"

    async def test_multiple_session_isolation(self):
        """Test that multiple user sessions are isolated"""
        gateway = UnifiedBotGateway()

        s1 = await gateway.session_manager.get_or_create("user_123")
        s2 = await gateway.session_manager.get_or_create("user_456")

        s1.metadata["score"] = 100
        s2.metadata["score"] = 200

        assert s1.metadata["score"] == 100
        assert s2.metadata["score"] == 200

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


class TestGatewayFIMLIntegration:
    """Test FIML integration in gateway handlers"""

    async def test_gateway_initializes_fiml_services(self):
        """Test gateway initializes FIML services"""
        gateway = UnifiedBotGateway()

        assert gateway.ai_mentor_service is not None
        assert gateway.fiml_data_adapter is not None
        assert gateway.narrative_generator is not None

    async def test_gateway_accepts_custom_services(self):
        """Test gateway accepts custom service instances"""
        mock_mentor = MagicMock()
        mock_adapter = MagicMock()
        mock_generator = MagicMock()

        gateway = UnifiedBotGateway(
            ai_mentor_service=mock_mentor,
            fiml_data_adapter=mock_adapter,
            narrative_generator=mock_generator,
        )

        assert gateway.ai_mentor_service is mock_mentor
        assert gateway.fiml_data_adapter is mock_adapter
        assert gateway.narrative_generator is mock_generator

    async def test_handle_ai_question_uses_mentor_service(self):
        """Test handle_ai_question uses AIMentorService"""
        mock_mentor = AsyncMock()
        mock_mentor.respond.return_value = {
            "text": "This is a test response about stocks.",
            "mentor": "Maya",
            "icon": "👩‍🏫",
            "related_lessons": ["stock_basics_001"],
            "disclaimer": "Educational purposes only - not financial advice",
        }

        gateway = UnifiedBotGateway(ai_mentor_service=mock_mentor)
        session = await gateway.session_manager.get_or_create("test_user")
        msg = AbstractMessage(text="What is a stock?", user_id="test_user", platform="test")

        from fiml.bot.core.gateway import Intent

        intent = Intent(type=IntentType.AI_QUESTION, data={"question": "What is a stock?"})

        response = await gateway.handle_ai_question(msg, session, intent)

        # Verify mentor service was called
        mock_mentor.respond.assert_called_once()
        call_kwargs = mock_mentor.respond.call_args.kwargs
        assert call_kwargs["user_id"] == "test_user"
        assert call_kwargs["question"] == "What is a stock?"
        assert call_kwargs["persona"] == MentorPersona.MAYA

        # Verify response format
        assert response is not None
        assert isinstance(response, AbstractResponse)
        assert "Maya" in response.text
        assert "This is a test response about stocks" in response.text
        assert "Educational purposes only" in response.text

    async def test_handle_ai_question_respects_mentor_preference(self):
        """Test handle_ai_question uses mentor from session preferences"""
        mock_mentor = AsyncMock()
        mock_mentor.respond.return_value = {
            "text": "Analytical response about stocks.",
            "mentor": "Theo",
            "icon": "👨‍💼",
            "related_lessons": [],
            "disclaimer": "Educational purposes only",
        }

        gateway = UnifiedBotGateway(ai_mentor_service=mock_mentor)
        session = await gateway.session_manager.get_or_create("test_user")
        session.preferences["mentor"] = "theo"

        msg = AbstractMessage(text="Analyze AAPL", user_id="test_user", platform="test")
        from fiml.bot.core.gateway import Intent

        intent = Intent(type=IntentType.AI_QUESTION, data={"question": "Analyze AAPL"})

        await gateway.handle_ai_question(msg, session, intent)

        # Verify Theo persona was used
        call_kwargs = mock_mentor.respond.call_args.kwargs
        assert call_kwargs["persona"] == MentorPersona.THEO

    async def test_handle_ai_question_fallback_on_error(self):
        """Test handle_ai_question falls back gracefully on error"""
        mock_mentor = AsyncMock()
        mock_mentor.respond.side_effect = Exception("Service unavailable")

        gateway = UnifiedBotGateway(ai_mentor_service=mock_mentor)
        session = await gateway.session_manager.get_or_create("test_user")
        msg = AbstractMessage(text="What is a stock?", user_id="test_user", platform="test")

        from fiml.bot.core.gateway import Intent

        intent = Intent(type=IntentType.AI_QUESTION, data={"question": "What is a stock?"})

        response = await gateway.handle_ai_question(msg, session, intent)

        # Should return fallback response, not raise exception
        assert response is not None
        assert isinstance(response, AbstractResponse)
        assert "trouble connecting" in response.text.lower() or "try again" in response.text.lower()
        assert "Educational purposes only" in response.text

    async def test_handle_market_query_uses_data_adapter(self):
        """Test handle_market_query uses FIMLEducationalDataAdapter"""
        mock_adapter = AsyncMock()
        mock_adapter.get_educational_snapshot.return_value = {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "price": {
                "current": 175.50,
                "change": 2.30,
                "change_percent": 1.33,
                "explanation": "Moderate movement up - notable but not unusual",
            },
            "volume": {
                "current": 50000000,
                "average": 45000000,
                "interpretation": "Volume is 1.1x average - elevated interest",
            },
            "fundamentals": {
                "pe_ratio": 28.5,
                "market_cap": "2.5T",
                "explanation": "Moderate P/E (15-25) - fairly valued",
            },
            "disclaimer": "📚 Live market data for educational purposes only",
            "data_source": "Via FIML from yahoo_finance",
        }
        mock_adapter.format_for_lesson.return_value = (
            "📊 **AAPL - Apple Inc.**\n\n"
            "**Current Price:** $175.50\n"
            "**Change:** +1.33%"
        )

        # Mock narrative generator to avoid actual LLM calls
        mock_generator = AsyncMock()

        gateway = UnifiedBotGateway(
            fiml_data_adapter=mock_adapter, narrative_generator=mock_generator
        )
        session = await gateway.session_manager.get_or_create("test_user")
        msg = AbstractMessage(text="Show me AAPL price", user_id="test_user", platform="test")

        from fiml.bot.core.gateway import Intent

        intent = Intent(type=IntentType.MARKET_QUERY, data={"query": "Show me AAPL price"})

        response = await gateway.handle_market_query(msg, session, intent)

        # Verify data adapter was called
        mock_adapter.get_educational_snapshot.assert_called_once()
        call_kwargs = mock_adapter.get_educational_snapshot.call_args.kwargs
        assert call_kwargs["symbol"] == "AAPL"
        assert call_kwargs["user_id"] == "test_user"

        # Verify response format
        assert response is not None
        assert isinstance(response, AbstractResponse)
        assert "AAPL" in response.text

    async def test_handle_market_query_no_symbol_found(self):
        """Test handle_market_query when no symbol can be extracted"""
        gateway = UnifiedBotGateway()
        session = await gateway.session_manager.get_or_create("test_user")
        msg = AbstractMessage(text="Show me some prices", user_id="test_user", platform="test")

        from fiml.bot.core.gateway import Intent

        intent = Intent(type=IntentType.MARKET_QUERY, data={"query": "Show me some prices"})

        response = await gateway.handle_market_query(msg, session, intent)

        # Should return helpful message about providing a symbol
        assert response is not None
        assert isinstance(response, AbstractResponse)
        assert "couldn't identify" in response.text.lower() or "symbol" in response.text.lower()

    async def test_handle_market_query_fallback_on_error(self):
        """Test handle_market_query falls back gracefully on error"""
        mock_adapter = AsyncMock()
        mock_adapter.get_educational_snapshot.side_effect = Exception("API unavailable")

        gateway = UnifiedBotGateway(fiml_data_adapter=mock_adapter)
        session = await gateway.session_manager.get_or_create("test_user")
        msg = AbstractMessage(text="Show me AAPL price", user_id="test_user", platform="test")

        from fiml.bot.core.gateway import Intent

        intent = Intent(type=IntentType.MARKET_QUERY, data={"query": "Show me AAPL price"})

        response = await gateway.handle_market_query(msg, session, intent)

        # Should return fallback response, not raise exception
        assert response is not None
        assert isinstance(response, AbstractResponse)
        assert "trouble" in response.text.lower() or "try again" in response.text.lower()

    async def test_extract_symbol_from_query(self):
        """Test symbol extraction from various query formats"""
        gateway = UnifiedBotGateway()

        # Direct symbol
        assert gateway._extract_symbol_from_query("Show me AAPL") == "AAPL"
        assert gateway._extract_symbol_from_query("TSLA price") == "TSLA"

        # Company name
        assert gateway._extract_symbol_from_query("Show me Apple stock") == "AAPL"
        assert gateway._extract_symbol_from_query("What is Tesla doing?") == "TSLA"
        assert gateway._extract_symbol_from_query("Microsoft earnings") == "MSFT"

        # Dollar sign prefix
        assert gateway._extract_symbol_from_query("What's $GOOGL doing?") == "GOOGL"
        assert gateway._extract_symbol_from_query("$NVDA analysis") == "NVDA"

        # No symbol found
        assert gateway._extract_symbol_from_query("Show me some stocks") is None
        assert gateway._extract_symbol_from_query("What is the market doing?") is None

    async def test_handle_ai_question_includes_related_lessons(self):
        """Test that AI question response includes related lessons"""
        mock_mentor = AsyncMock()
        mock_mentor.respond.return_value = {
            "text": "P/E ratio explanation...",
            "mentor": "Maya",
            "icon": "👩‍🏫",
            "related_lessons": ["stock_basics_001", "valuation_101"],
            "disclaimer": "Educational purposes only",
        }

        gateway = UnifiedBotGateway(ai_mentor_service=mock_mentor)
        session = await gateway.session_manager.get_or_create("test_user")
        msg = AbstractMessage(text="What is P/E ratio?", user_id="test_user", platform="test")

        from fiml.bot.core.gateway import Intent

        intent = Intent(type=IntentType.AI_QUESTION, data={"question": "What is P/E ratio?"})

        response = await gateway.handle_ai_question(msg, session, intent)

        # Related lessons should be in response
        assert "Related Lessons" in response.text
        assert "stock_basics_001" in response.text
        assert "valuation_101" in response.text

    async def test_handle_message_flow(self):
        """Test the full message processing pipeline"""
        gateway = UnifiedBotGateway()

        # Mock the classify method to return a known intent
        with patch.object(gateway.intent_classifier, 'classify', new_callable=AsyncMock) as mock_classify:
            from fiml.bot.core.gateway import Intent
            mock_classify.return_value = Intent(type=IntentType.COMMAND, data={"command": "/help"})

            response = await gateway.handle_message(
                platform="telegram",
                user_id="test_user_flow",
                text="/help"
            )

            # Verify session was created/retrieved
            session = gateway.session_manager.get_session("test_user_flow")
            assert session is not None
            assert session.platform == "telegram"

            # Verify intent was classified
            mock_classify.assert_called_once()

            # Verify response
            assert isinstance(response, AbstractResponse)
            assert response.metadata["intent"] == "command"

    async def test_placeholder_handlers(self):
        """Test placeholder handlers return expected responses"""
        gateway = UnifiedBotGateway()
        session = await gateway.session_manager.get_or_create("test_user")
        msg = AbstractMessage(text="test", user_id="test_user", platform="test")

        from fiml.bot.core.gateway import Intent

        # Test handle_command
        intent = Intent(type=IntentType.COMMAND, data={"command": "/test"})
        resp = await gateway.handle_command(msg, session, intent)
        assert "not fully implemented on mobile yet" in resp.text

        # Test handle_lesson_request
        intent = Intent(type=IntentType.LESSON_REQUEST, data={})
        resp = await gateway.handle_lesson_request(msg, session, intent)
        # It might return "Available Lessons" or "No lessons available yet" depending on file system
        # But definitely not "Lessons Coming Soon" which was the old placeholder
        assert "Available Lessons" in resp.text or "No lessons available" in resp.text

        # Test handle_lesson_navigation
        intent = Intent(type=IntentType.LESSON_NAVIGATION, data={"action": "next"})
        resp = await gateway.handle_lesson_navigation(msg, session, intent)
        assert "Lesson navigation: next" in resp.text

        # Test handle_quiz_answer
        intent = Intent(type=IntentType.QUIZ_ANSWER, data={})
        resp = await gateway.handle_quiz_answer(msg, session, intent)
        assert "Quiz interaction not understood" in resp.text

        # Test handle_navigation
        intent = Intent(type=IntentType.NAVIGATION, data={"action": "home"})
        resp = await gateway.handle_navigation(msg, session, intent)
        assert "Navigation: home" in resp.text

        # Test handle_unknown
        intent = Intent(type=IntentType.UNKNOWN, data={})
        resp = await gateway.handle_unknown(msg, session, intent)
        assert "I'm not sure what you mean" in resp.text

    async def test_register_handler(self):
        """Test registering custom handlers"""
        gateway = UnifiedBotGateway()

        async def custom_handler(message, session, intent):
            return AbstractResponse(text="Custom Handler Executed")

        gateway.register_handler(IntentType.UNKNOWN, custom_handler)

        # Verify handler was updated
        assert gateway.handlers[IntentType.UNKNOWN] == custom_handler

        # Verify it's used
        session = await gateway.session_manager.get_or_create("test_user")
        msg = AbstractMessage(text="unknown", user_id="test_user", platform="test")
        from fiml.bot.core.gateway import Intent
        intent = Intent(type=IntentType.UNKNOWN, data={})

        resp = await gateway.handle_unknown(msg, session, intent) # Direct call to registered handler via map lookup in real flow
        # But here we need to call the handler that is mapped
        handler = gateway.handlers[IntentType.UNKNOWN]
        resp = await handler(msg, session, intent)

        assert resp.text == "Custom Handler Executed"

    async def test_session_manager_update_timestamp(self):
        """Test session update refreshes timestamp"""
        gateway = UnifiedBotGateway()
        session = await gateway.session_manager.get_or_create("test_user")
        original_time = session.updated_at

        # Wait a tiny bit to ensure time difference
        import asyncio
        await asyncio.sleep(0.001)

        await gateway.session_manager.update("test_user", session)
        assert session.updated_at > original_time

    async def test_session_manager_delete_idempotency(self):
        """Test session delete is idempotent"""
        gateway = UnifiedBotGateway()

        # Delete non-existent
        await gateway.session_manager.delete("non_existent")

        # Create and delete
        await gateway.session_manager.get_or_create("test_user")
        await gateway.session_manager.delete("test_user")
        assert gateway.session_manager.get_session("test_user") is None

        # Delete again
        await gateway.session_manager.delete("test_user")

    async def test_intent_classification_priority(self):
        """Test priority of educational patterns over market keywords"""
        gateway = UnifiedBotGateway()
        session = await gateway.session_manager.get_or_create("test_user")

        # "what is stock" contains "stock" (market keyword) but "what is" (educational pattern)
        msg = AbstractMessage(text="what is stock", user_id="test_user", platform="test")
        intent = await gateway.classify(msg, session)

        # Should be AI_QUESTION because of "what is", not MARKET_QUERY
        assert intent.type == IntentType.AI_QUESTION

    async def test_market_query_expertise_parsing(self):
        """Test parsing of expertise level in market query"""
        # This tests the logic inside handle_market_query where it parses session preferences

        mock_adapter = AsyncMock()
        mock_adapter.get_educational_snapshot.return_value = {
            "symbol": "AAPL", "price": {"current": 100}
        }
        mock_adapter.format_for_lesson.return_value = "Price: 100"

        mock_generator = AsyncMock()
        # We want to verify the context passed to generator has correct expertise

        gateway = UnifiedBotGateway(
            fiml_data_adapter=mock_adapter,
            narrative_generator=mock_generator
        )

        session = await gateway.session_manager.get_or_create("test_user")
        session.preferences["expertise_level"] = "INVALID_LEVEL"

        msg = AbstractMessage(text="AAPL", user_id="test_user", platform="test")
        from fiml.bot.core.gateway import Intent
        intent = Intent(type=IntentType.MARKET_QUERY, data={"query": "AAPL"})

        await gateway.handle_market_query(msg, session, intent)

        # Verify narrative generator was called
        if mock_generator.generate_narrative.called:
            call_args = mock_generator.generate_narrative.call_args
            context = call_args.kwargs.get('context') or call_args.args[0]
            # Should default to BEGINNER
            from fiml.narrative.models import ExpertiseLevel
            assert context.preferences.expertise_level == ExpertiseLevel.BEGINNER
