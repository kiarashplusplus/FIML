"""
Component 3: Unified Bot Gateway
Central message processing hub for multi-platform educational bot
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, cast

import structlog

from fiml.bot.education.ai_mentor import AIMentorService, MentorPersona
from fiml.bot.education.fiml_adapter import FIMLEducationalDataAdapter
from fiml.narrative.generator import NarrativeGenerator
from fiml.narrative.models import (
    ExpertiseLevel,
    Language,
    NarrativeContext,
    NarrativePreferences,
)

logger = structlog.get_logger(__name__)


class IntentType(Enum):
    """Types of user intents"""

    COMMAND = "command"
    LESSON_REQUEST = "lesson_request"
    LESSON_NAVIGATION = "lesson_navigation"
    QUIZ_ANSWER = "quiz_answer"
    AI_QUESTION = "ai_question"
    MARKET_QUERY = "market_query"
    KEY_MANAGEMENT = "key_management"
    NAVIGATION = "navigation"
    UNKNOWN = "unknown"


@dataclass
class AbstractMessage:
    """Platform-agnostic message representation"""

    user_id: str
    platform: str
    text: str
    media: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.media is None:
            self.media = []
        if self.context is None:
            self.context = {}
        if self.timestamp is None:
            self.timestamp = datetime.now(UTC)


@dataclass
class AbstractResponse:
    """Platform-agnostic response representation"""

    text: str
    media: Optional[List[str]] = None
    actions: Optional[List[Dict[str, Any]]] = None  # Buttons, keyboards
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.media is None:
            self.media = []
        if self.actions is None:
            self.actions = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Intent:
    """Parsed user intent"""

    type: IntentType
    data: Dict[str, Any]
    confidence: float = 1.0


class SessionState(Enum):
    """User session states"""

    NEW_USER = "new_user"
    ONBOARDING = "onboarding"
    IN_LESSON = "in_lesson"
    IN_QUIZ = "in_quiz"
    IN_CONVERSATION = "in_conversation"
    IDLE = "idle"


@dataclass
class UserSession:
    """User session data"""

    user_id: str
    platform: str
    state: SessionState
    current_lesson: Optional[str] = None
    current_quiz: Optional[str] = None
    current_question: Optional[int] = None
    conversation_history: Optional[List[Dict[str, Any]]] = None
    progress: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.conversation_history is None:
            self.conversation_history = []
        if self.progress is None:
            self.progress = {}
        if self.preferences is None:
            self.preferences = {"mentor": "maya"}
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now(UTC)
        if self.updated_at is None:
            self.updated_at = datetime.now(UTC)


class SessionManager:
    """Manages user sessions across platforms"""

    def __init__(self) -> None:
        # In-memory storage (should be Redis in production)
        self._sessions: Dict[str, UserSession] = {}
        logger.info("SessionManager initialized")

    async def get_or_create(self, user_id: str, platform: str = "telegram") -> UserSession:
        """Get existing session or create new one"""
        if user_id in self._sessions:
            session = self._sessions[user_id]
            session.updated_at = datetime.now(UTC)
            return session

        # Create new session
        session = UserSession(user_id=user_id, platform=platform, state=SessionState.NEW_USER)
        self._sessions[user_id] = session

        logger.info("New session created", user_id=user_id, platform=platform)
        return session

    async def update(self, user_id: str, session: UserSession) -> None:
        """Update session"""
        session.updated_at = datetime.now(UTC)
        self._sessions[user_id] = session
        logger.debug("Session updated", user_id=user_id)

    async def delete(self, user_id: str) -> None:
        """Delete session"""
        if user_id in self._sessions:
            del self._sessions[user_id]
            logger.info("Session deleted", user_id=user_id)

    def get_session(self, user_id: str) -> Optional[UserSession]:
        """Get session without creating if it doesn't exist"""
        return self._sessions.get(user_id)


class IntentClassifier:
    """Classifies user messages into intents"""

    # Command keywords
    COMMANDS = {
        "/start",
        "/help",
        "/lesson",
        "/quiz",
        "/mentor",
        "/market",
        "/addkey",
        "/listkeys",
        "/removekey",
        "/testkey",
        "/status",
        "/progress",
        "/cancel",
    }

    # Lesson keywords
    LESSON_KEYWORDS = ["lesson", "learn", "teach", "explain", "course", "module"]

    # Educational question patterns (high priority)
    EDUCATIONAL_PATTERNS = [
        "what is",
        "how do",
        "can you explain",
        "what's the difference",
        "how does",
        "why does",
        "tell me about",
        "what are",
    ]

    # Market keywords
    MARKET_KEYWORDS = ["price", "stock", "chart", "quote", "$", "market", "ticker"]

    # Navigation keywords
    NAVIGATION_KEYWORDS = ["next", "back", "menu", "home", "continue", "skip"]

    async def classify(self, message: AbstractMessage, session: UserSession) -> Intent:
        """
        Classify message intent based on content and context

        Args:
            message: User message
            session: User session

        Returns:
            Classified intent
        """
        text = message.text.lower().strip()

        # Check for commands
        if text.startswith("/"):
            command = text.split()[0]
            return Intent(type=IntentType.COMMAND, data={"command": command}, confidence=1.0)

        # Context-based classification
        if session.state == SessionState.IN_QUIZ:
            return Intent(
                type=IntentType.QUIZ_ANSWER, data={"answer": message.text}, confidence=0.9
            )

        if session.state == SessionState.IN_LESSON:
            if any(kw in text for kw in self.NAVIGATION_KEYWORDS):
                return Intent(
                    type=IntentType.LESSON_NAVIGATION, data={"action": text}, confidence=0.8
                )

        # Check for educational questions first (higher priority than market keywords)
        if any(pattern in text for pattern in self.EDUCATIONAL_PATTERNS):
            return Intent(
                type=IntentType.AI_QUESTION, data={"question": message.text}, confidence=0.8
            )

        # Keyword-based classification
        if any(kw in text for kw in self.LESSON_KEYWORDS):
            return Intent(
                type=IntentType.LESSON_REQUEST, data={"query": message.text}, confidence=0.7
            )

        if any(kw in text for kw in self.MARKET_KEYWORDS):
            return Intent(
                type=IntentType.MARKET_QUERY, data={"query": message.text}, confidence=0.7
            )

        if any(kw in text for kw in self.NAVIGATION_KEYWORDS):
            return Intent(type=IntentType.NAVIGATION, data={"action": text}, confidence=0.6)

        # Default to AI question
        return Intent(type=IntentType.AI_QUESTION, data={"question": message.text}, confidence=0.5)


class UnifiedBotGateway:
    """
    Central message processing hub for multi-platform bot

    Features:
    - Platform-agnostic message handling
    - Intent classification
    - Session management
    - Handler routing
    - Response formatting
    - Integration with FIML Narrative Generation Engine
    """

    def __init__(
        self,
        ai_mentor_service: Optional[AIMentorService] = None,
        fiml_data_adapter: Optional[FIMLEducationalDataAdapter] = None,
        narrative_generator: Optional[NarrativeGenerator] = None,
    ) -> None:
        self.session_manager = SessionManager()
        self.intent_classifier: IntentClassifier = IntentClassifier()

        # Initialize FIML services for narrative generation
        self.narrative_generator = narrative_generator or NarrativeGenerator()
        self.ai_mentor_service = ai_mentor_service or AIMentorService(
            narrative_generator=self.narrative_generator
        )
        self.fiml_data_adapter = fiml_data_adapter or FIMLEducationalDataAdapter()

        # Handlers will be set by components
        self.handlers: Dict[IntentType, Any] = {
            IntentType.COMMAND: self.handle_command,
            IntentType.LESSON_REQUEST: self.handle_lesson_request,
            IntentType.LESSON_NAVIGATION: self.handle_lesson_navigation,
            IntentType.QUIZ_ANSWER: self.handle_quiz_answer,
            IntentType.AI_QUESTION: self.handle_ai_question,
            IntentType.MARKET_QUERY: self.handle_market_query,
            IntentType.NAVIGATION: self.handle_navigation,
            IntentType.UNKNOWN: self.handle_unknown,
        }

        logger.info("UnifiedBotGateway initialized with FIML narrative generation")

    async def classify(self, message: AbstractMessage, session: UserSession) -> Intent:
        """
        Classify message intent

        Args:
            message: User message
            session: User session

        Returns:
            Classified intent
        """
        return await self.intent_classifier.classify(message, session)

    async def handle_message(
        self, platform: str, user_id: str, text: str, context: Optional[Dict] = None
    ) -> AbstractResponse:
        """
        Main message processing pipeline

        Args:
            platform: Platform identifier (telegram, web, whatsapp)
            user_id: User identifier
            text: Message text
            context: Additional context

        Returns:
            Abstract response
        """
        # 1. Create abstract message
        message = AbstractMessage(
            user_id=user_id, platform=platform, text=text, context=context or {}
        )

        # 2. Load user session
        session = await self.session_manager.get_or_create(user_id, platform)

        # 3. Classify intent
        intent = await self.intent_classifier.classify(message, session)

        logger.info(
            "Message classified",
            user_id=user_id,
            intent_type=intent.type.value,
            confidence=intent.confidence,
        )

        # 4. Route to handler
        handler = self.handlers.get(intent.type, self.handle_unknown)
        response = await handler(message, session, intent)

        # 5. Update session
        await self.session_manager.update(user_id, session)

        # 6. Add metadata
        response.metadata["intent"] = intent.type.value
        response.metadata["confidence"] = intent.confidence

        return cast(AbstractResponse, response)

    async def handle_command(
        self, message: AbstractMessage, session: UserSession, intent: Intent
    ) -> AbstractResponse:
        """Handle bot commands"""
        command = intent.data.get("command", "")

        # These are handled by platform adapters
        # This is a fallback for when gateway receives commands
        return AbstractResponse(
            text=f"Command {command} should be handled by platform adapter",
            metadata={"handled_by": "gateway_fallback"},
        )

    async def handle_lesson_request(
        self, message: AbstractMessage, session: UserSession, intent: Intent
    ) -> AbstractResponse:
        """Handle lesson requests"""
        # Placeholder - will be implemented by LessonContentEngine
        return AbstractResponse(
            text="📚 **Lessons Coming Soon!**\n\n"
            "The lesson system is being built. Soon you'll be able to:\n"
            "- Learn trading fundamentals\n"
            "- Practice with real market data\n"
            "- Take interactive quizzes\n\n"
            "For now, try:\n"
            "/help - See available commands\n"
            "/addkey - Add API keys for market data"
        )

    async def handle_lesson_navigation(
        self, message: AbstractMessage, session: UserSession, intent: Intent
    ) -> AbstractResponse:
        """Handle lesson navigation"""
        action = intent.data.get("action", "")

        # Placeholder
        return AbstractResponse(
            text=f"Lesson navigation: {action}\n\n" "(Lesson system coming soon)"
        )

    async def handle_quiz_answer(
        self, message: AbstractMessage, session: UserSession, intent: Intent
    ) -> AbstractResponse:
        """Handle quiz answers"""
        # Placeholder - will be implemented by QuizSystem
        return AbstractResponse(
            text="Quiz system coming soon!\n\n"
            "You'll be able to test your knowledge with interactive quizzes."
        )

    async def handle_ai_question(
        self, message: AbstractMessage, session: UserSession, intent: Intent
    ) -> AbstractResponse:
        """Handle AI mentor questions using FIML Narrative Generation Engine"""
        question = intent.data.get("question", "")

        try:
            # Get mentor persona from session preferences (default to Maya)
            mentor_name = session.preferences.get("mentor", "maya").lower()
            try:
                persona = MentorPersona(mentor_name)
            except ValueError:
                persona = MentorPersona.MAYA

            # Use AIMentorService to generate response via NarrativeGenerator
            response_data = await self.ai_mentor_service.respond(
                user_id=message.user_id,
                question=question,
                persona=persona,
                context=message.context,
            )

            # Format the response with mentor icon and disclaimer
            mentor_icon = response_data.get("icon", "🤖")
            mentor_name = response_data.get("mentor", "Maya")
            response_text = response_data.get("text", "")
            disclaimer = response_data.get(
                "disclaimer", "Educational purposes only - not financial advice"
            )

            # Add related lesson suggestions if available
            related_lessons = response_data.get("related_lessons", [])
            lessons_text = ""
            if related_lessons:
                lessons_text = "\n\n📚 **Related Lessons:**\n" + "\n".join(
                    [f"• {lesson}" for lesson in related_lessons]
                )

            formatted_response = (
                f"{mentor_icon} **{mentor_name}:**\n\n"
                f"{response_text}{lessons_text}\n\n"
                f"_{disclaimer}_"
            )

            logger.info(
                "AI mentor response generated",
                user_id=message.user_id,
                persona=persona.value,
                question_length=len(question),
            )

            return AbstractResponse(
                text=formatted_response,
                metadata={"mentor": mentor_name, "persona": persona.value},
            )

        except Exception as e:
            # Graceful fallback to template response if FIML services unavailable
            logger.warning(
                "Failed to generate AI mentor response, using fallback",
                user_id=message.user_id,
                error=str(e),
            )

            return AbstractResponse(
                text="🤖 **AI Mentor:**\n\n"
                f"You asked: _{question}_\n\n"
                "I'm having trouble connecting to my knowledge base right now. "
                "Please try again in a moment, or explore:\n"
                "• /lesson - Browse available lessons\n"
                "• /help - See what I can help with\n\n"
                "_Educational purposes only - not financial advice_"
            )

    async def handle_market_query(
        self, message: AbstractMessage, session: UserSession, intent: Intent
    ) -> AbstractResponse:
        """Handle market data queries using FIML Educational Data Adapter"""
        query = intent.data.get("query", "")

        try:
            # Extract symbol from the query
            symbol = self._extract_symbol_from_query(query)

            if not symbol:
                return AbstractResponse(
                    text="📊 **Market Data Query**\n\n"
                    "I couldn't identify a specific stock or crypto symbol in your query.\n\n"
                    "Try asking about a specific symbol like:\n"
                    "• 'Show me AAPL price'\n"
                    "• 'What's the price of TSLA stock?'\n"
                    "• 'Tell me about MSFT'\n\n"
                    "_Educational purposes only - not financial advice_"
                )

            # Use FIMLEducationalDataAdapter to fetch market data with educational context
            educational_data = await self.fiml_data_adapter.get_educational_snapshot(
                symbol=symbol, user_id=message.user_id, context="mentor"
            )

            # Format the educational snapshot for display
            formatted_data = await self.fiml_data_adapter.format_for_lesson(educational_data)

            # Generate educational narrative using NarrativeGenerator if available
            narrative_text = ""
            try:
                # Get user's expertise level from session (default to beginner)
                expertise_str = session.preferences.get("expertise_level", "beginner")
                try:
                    expertise_level = ExpertiseLevel(expertise_str.lower())
                except ValueError:
                    expertise_level = ExpertiseLevel.BEGINNER

                # Build narrative context from the educational data
                price_info = educational_data.get("price", {})
                narrative_context = NarrativeContext(
                    asset_symbol=symbol,
                    asset_name=educational_data.get("name", f"{symbol} Stock"),
                    asset_type="stock",
                    market="US",
                    price_data={
                        "price": price_info.get("current", 0),
                        "change": price_info.get("change", 0),
                        "change_percent": price_info.get("change_percent", 0),
                    },
                    preferences=NarrativePreferences(
                        expertise_level=expertise_level,
                        language=Language.ENGLISH,
                        include_disclaimers=True,
                        include_technical=False,
                        include_fundamental=True,
                        include_sentiment=False,
                        include_risk=False,
                    ),
                    include_disclaimers=True,
                )

                # Generate a brief narrative summary
                narrative = await self.narrative_generator.generate_narrative(
                    context=narrative_context
                )
                narrative_text = f"\n\n📝 **Educational Insight:**\n{narrative.summary[:500]}..."

            except Exception as narrative_error:
                logger.debug(
                    "Narrative generation skipped",
                    symbol=symbol,
                    error=str(narrative_error),
                )

            response_text = (
                f"📊 **Market Data for {symbol}**\n\n"
                f"{formatted_data}{narrative_text}\n\n"
                f"_Source: {educational_data.get('data_source', 'FIML')}_\n"
                f"_{educational_data.get('disclaimer', 'Educational purposes only - not financial advice')}_"
            )

            logger.info(
                "Market query response generated",
                user_id=message.user_id,
                symbol=symbol,
            )

            return AbstractResponse(
                text=response_text,
                metadata={"symbol": symbol, "has_narrative": bool(narrative_text)},
            )

        except Exception as e:
            # Graceful fallback if FIML services are unavailable
            logger.warning(
                "Failed to generate market query response, using fallback",
                user_id=message.user_id,
                query=query,
                error=str(e),
            )

            return AbstractResponse(
                text="📊 **Market Data:**\n\n"
                f"You asked about: _{query}_\n\n"
                "I'm having trouble fetching market data right now. "
                "This could be due to:\n"
                "• API keys not configured (/addkey to set up)\n"
                "• Temporary service issues\n\n"
                "Try again in a moment, or set up your API keys first:\n"
                "• /addkey - Add provider keys\n"
                "• /listkeys - View connected providers\n\n"
                "_Educational purposes only - not financial advice_"
            )

    def _extract_symbol_from_query(self, query: str) -> Optional[str]:
        """
        Extract stock/crypto symbol from user query.

        Args:
            query: User's query text

        Returns:
            Detected symbol or None
        """
        query_upper = query.upper()

        # Common stock symbols to look for
        common_symbols = [
            "AAPL",
            "GOOGL",
            "GOOG",
            "MSFT",
            "AMZN",
            "TSLA",
            "META",
            "NVDA",
            "JPM",
            "V",
            "WMT",
            "PG",
            "JNJ",
            "UNH",
            "DIS",
            "NFLX",
            "PYPL",
            "INTC",
            "CSCO",
            "VZ",
            "PFE",
            "KO",
            "PEP",
            "NKE",
            "MCD",
            "BA",
            "GE",
            "IBM",
            "GM",
            "F",
            "T",
            "XOM",
            "CVX",
            "ORCL",
            "CRM",
            "AMD",
            "SPY",
            "QQQ",
            "BTC",
            "ETH",
        ]

        # Check for explicit symbol mentions
        words = query_upper.split()
        for word in words:
            # Remove common punctuation
            clean_word = word.strip(".,!?$")
            if clean_word in common_symbols:
                return clean_word

        # Check for company name mentions
        company_map = {
            "APPLE": "AAPL",
            "GOOGLE": "GOOGL",
            "ALPHABET": "GOOGL",
            "MICROSOFT": "MSFT",
            "AMAZON": "AMZN",
            "TESLA": "TSLA",
            "FACEBOOK": "META",
            "NVIDIA": "NVDA",
            "NETFLIX": "NFLX",
            "DISNEY": "DIS",
            "BITCOIN": "BTC",
            "ETHEREUM": "ETH",
        }

        for company_name, symbol in company_map.items():
            if company_name in query_upper:
                return symbol

        # Check for $ prefix (e.g., $AAPL)
        import re

        dollar_match = re.search(r"\$([A-Z]{1,5})", query_upper)
        if dollar_match:
            return dollar_match.group(1)

        return None

    async def handle_navigation(
        self, message: AbstractMessage, session: UserSession, intent: Intent
    ) -> AbstractResponse:
        """Handle general navigation"""
        action = intent.data.get("action", "")

        return AbstractResponse(
            text=f"Navigation: {action}\n\n" "Use /help to see available commands"
        )

    async def handle_unknown(
        self, message: AbstractMessage, session: UserSession, intent: Intent
    ) -> AbstractResponse:
        """Handle unknown intents"""
        return AbstractResponse(
            text="I'm not sure what you mean. 🤔\n\n"
            "Try these commands:\n"
            "/help - See all commands\n"
            "/lesson - Start learning (coming soon)\n"
            "/addkey - Set up your API keys"
        )

    def register_handler(self, intent_type: IntentType, handler: Any) -> None:
        """Register custom handler for intent type"""
        self.handlers[intent_type] = handler
        logger.info("Handler registered", intent_type=intent_type.value)
