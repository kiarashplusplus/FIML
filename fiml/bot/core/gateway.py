"""
Component 3: Unified Bot Gateway
Central message processing hub for multi-platform educational bot
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, cast

import structlog

from fiml.bot.education.ai_mentor import AIMentorService, MentorPersona
from fiml.bot.education.fiml_adapter import FIMLEducationalDataAdapter
from fiml.bot.education.gamification import GamificationEngine
from fiml.bot.education.lesson_engine import LessonContentEngine
from fiml.bot.education.quiz_system import QuizSystem
from fiml.narrative.generator import NarrativeGenerator
from fiml.narrative.models import (
    ExpertiseLevel,
    Language,
    NarrativeContext,
    NarrativePreferences,
)

logger = structlog.get_logger(__name__)

# Maximum length for narrative summary in market query responses
MAX_NARRATIVE_SUMMARY_LENGTH = 500

# Common stock and crypto symbols for extraction from user queries
COMMON_SYMBOLS = [
    "AAPL", "GOOGL", "GOOG", "MSFT", "AMZN", "TSLA", "META", "NVDA",
    "JPM", "V", "WMT", "PG", "JNJ", "UNH", "DIS", "NFLX", "PYPL",
    "INTC", "CSCO", "VZ", "PFE", "KO", "PEP", "NKE", "MCD", "BA",
    "GE", "IBM", "GM", "F", "T", "XOM", "CVX", "ORCL", "CRM", "AMD",
    "SPY", "QQQ", "BTC", "ETH",
]

# Mapping of company names to stock symbols
COMPANY_TO_SYMBOL = {
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
    GREETING = "greeting"
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

    # Greeting keywords
    GREETING_KEYWORDS = ["hi", "hello", "hey", "greetings", "yo", "start", "welcome"]

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
        
        # Check for explicit action in context (from mobile app buttons)
        context_action = message.context.get("action", "")
        if context_action:
            if context_action.startswith("lesson:"):
                return Intent(
                    type=IntentType.LESSON_NAVIGATION, 
                    data={"action": context_action}, 
                    confidence=1.0
                )
            elif context_action.startswith("quiz:"):
                return Intent(
                    type=IntentType.QUIZ_ANSWER, 
                    data={"answer": context_action}, 
                    confidence=1.0
                )
            elif context_action.startswith("/"):
                # Handle commands sent via context action
                command = context_action.split()[0]
                return Intent(
                    type=IntentType.COMMAND, 
                    data={"command": command}, 
                    confidence=1.0
                )

        # Check for commands
        if text.startswith("/"):
            command = text.split()[0]
            return Intent(type=IntentType.COMMAND, data={"command": command}, confidence=1.0)

        # Check for greetings
        if any(kw == text or text.startswith(kw + " ") for kw in self.GREETING_KEYWORDS):
            return Intent(type=IntentType.GREETING, data={"greeting": message.text}, confidence=0.9)

        # Context-based classification
        if session.state == SessionState.IN_QUIZ:
            # If in quiz, treat text as answer unless it's a command
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
        
        # Initialize educational engines
        self.lesson_engine = LessonContentEngine()
        self.quiz_system = QuizSystem()
        self.gamification = GamificationEngine()

        # Handlers will be set by components
        self.handlers: Dict[IntentType, Any] = {
            IntentType.COMMAND: self.handle_command,
            IntentType.LESSON_REQUEST: self.handle_lesson_request,
            IntentType.LESSON_NAVIGATION: self.handle_lesson_navigation,
            IntentType.QUIZ_ANSWER: self.handle_quiz_answer,
            IntentType.AI_QUESTION: self.handle_ai_question,
            IntentType.MARKET_QUERY: self.handle_market_query,
            IntentType.NAVIGATION: self.handle_navigation,
            IntentType.MARKET_QUERY: self.handle_market_query,
            IntentType.NAVIGATION: self.handle_navigation,
            IntentType.GREETING: self.handle_greeting,
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
        command = intent.data.get("command", "").lower()
        
        if command == "/help":
            return AbstractResponse(
                text="📚 FIML Educational Bot Commands\n\n"
                     "Key Management:\n"
                     "/addkey - Add a new API key\n"
                     "/listkeys - View your connected providers\n"
                     "/removekey - Remove an API key\n"
                     "/testkey - Test if your keys are working\n"
                     "/status - View your provider status and usage\n\n"
                     "Learning:\n"
                     "/lesson - Browse and start lessons\n"
                     "/quiz - Take a practice quiz\n"
                     "/mentor - Talk to AI mentor\n"
                     "/progress - View your learning progress\n\n"
                     "Advanced Analysis:\n"
                     "/fkdsl - Run Financial Knowledge DSL queries",
                actions=[
                    {"text": "Start Learning", "action": "/lesson", "type": "primary"},
                    {"text": "Add API Key", "action": "/addkey", "type": "secondary"},
                    {"text": "Ask Mentor", "action": "/mentor", "type": "secondary"},
                ]
            )
            
        elif command == "/lesson":
            # Delegate to lesson request handler
            return await self.handle_lesson_request(message, session, intent)
            
        elif command == "/quiz":
            # Start a quiz for the current or last lesson
            if session.current_lesson:
                # Logic to start quiz for current lesson
                return await self.start_quiz_for_lesson(session.current_lesson, message.user_id)
            else:
                return AbstractResponse(
                    text="You haven't started a lesson yet. Start a lesson to take a quiz!",
                    actions=[{"text": "Browse Lessons", "action": "/lesson", "type": "primary"}]
                )

        elif command == "/mentor":
             return AbstractResponse(
                text="👋 I'm your AI Mentor.\n\n"
                     "Ask me anything about trading, markets, or financial concepts.\n"
                     "Try: 'What is a stop loss?' or 'Explain P/E ratio'",
                actions=[]
            )

        elif command == "/addkey":
             return AbstractResponse(
                text="🔑 Add API Key\n\n"
                     "To add an API key, please use the /addkey command followed by the provider name and key.\n"
                     "Example: `/addkey binance <your_api_key>`\n\n"
                     "Or use the web dashboard for easier management.",
                actions=[{"text": "Open Dashboard", "url": "/dashboard", "type": "link"}] # Placeholder URL
            )
            
        elif command == "/progress":
             progress = await self.lesson_engine.get_user_progress(message.user_id)
             completed = len(progress.get("completed", []))
             return AbstractResponse(
                text=f"📈 Your Progress\n\n"
                     f"Lessons Completed: {completed}\n"
                     f"Current Streak: {session.metadata.get('streak', 0)} days\n"
                     f"Total XP: {session.metadata.get('xp', 0)}",
                actions=[{"text": "Continue Learning", "action": "/lesson", "type": "primary"}]
            )

        return AbstractResponse(
            text=f"Command {command} is not fully implemented on mobile yet.",
            metadata={"handled_by": "gateway_fallback"},
        )

    async def handle_lesson_request(
        self, message: AbstractMessage, session: UserSession, intent: Intent
    ) -> AbstractResponse:
        """Handle lesson requests"""
        # Get available lessons (using private method logic from adapter, adapted here)
        # In a real scenario, LessonContentEngine should expose this public method
        # For now, we'll list hardcoded basics if engine doesn't support listing yet
        
        # We need to list lessons. 
        # Ideally LessonContentEngine should have list_lessons()
        # Let's assume we can get them or use a static list for now
        
        lessons = [
            {"id": "stock_basics_001", "title": "Understanding Stock Prices", "difficulty": "beginner"},
            {"id": "stock_basics_002", "title": "Market Orders vs Limit Orders", "difficulty": "beginner"},
            {"id": "stock_basics_003", "title": "Volume and Liquidity", "difficulty": "beginner"},
            {"id": "valuation_001", "title": "Understanding P/E Ratio", "difficulty": "intermediate"},
            {"id": "risk_001", "title": "Position Sizing and Risk", "difficulty": "intermediate"},
        ]
        
        actions = []
        for lesson in lessons:
            actions.append({
                "text": f"{lesson['title']} ({lesson['difficulty']})",
                "action": f"lesson:start:{lesson['id']}",
                "type": "secondary"
            })
            
        return AbstractResponse(
            text="📚 Available Lessons\n\nSelect a lesson to start learning:",
            actions=actions
        )

    async def handle_lesson_navigation(
        self, message: AbstractMessage, session: UserSession, intent: Intent
    ) -> AbstractResponse:
        """Handle lesson navigation"""
        action = intent.data.get("action", "")
        
        if action.startswith("lesson:start:"):
            lesson_id = action.split(":")[-1]
            
            # Load and render lesson
            lesson = await self.lesson_engine.load_lesson(lesson_id)
            if not lesson:
                # Create sample if missing (for demo)
                self.lesson_engine.create_sample_lesson(lesson_id)
                lesson = await self.lesson_engine.load_lesson(lesson_id)
                
            if lesson:
                rendered = await self.lesson_engine.render_lesson(lesson, message.user_id)
                self.lesson_engine.mark_lesson_started(message.user_id, lesson_id)
                
                # Update session
                session.current_lesson = lesson_id
                session.state = SessionState.IN_LESSON
                
                return AbstractResponse(
                    text=rendered.content,
                    actions=[
                        {"text": "Take Quiz", "action": f"quiz:start:{lesson_id}", "type": "primary"},
                        {"text": "Back to Lessons", "action": "/lesson", "type": "secondary"}
                    ]
                )
            else:
                 return AbstractResponse(text="❌ Lesson not found.")

        return AbstractResponse(
            text=f"Lesson navigation: {action}"
        )

    async def handle_quiz_answer(
        self, message: AbstractMessage, session: UserSession, intent: Intent
    ) -> AbstractResponse:
        """Handle quiz answers"""
        action = intent.data.get("answer", "") # Can be answer text or callback data
        
        # Parse action if it's a callback string
        if isinstance(action, str) and action.startswith("quiz:start:"):
            lesson_id = action.split(":")[-1]
            return await self.start_quiz_for_lesson(lesson_id, message.user_id)
            
        if isinstance(action, str) and action.startswith("quiz:answer:"):
            # Format: quiz:answer:session_id:question_index:answer_value
            parts = action.split(":")
            if len(parts) >= 5:
                session_id = parts[2]
                # q_idx = int(parts[3]) # Not needed for submit_answer if we trust session state or if submit_answer handles it
                answer_val = parts[4]
                
                result = await self.quiz_system.submit_answer(session_id, answer_val)
                
                if result.get("error"):
                    return AbstractResponse(text=f"❌ Error: {result['error']}")
                    
                response_text = f"{'✅ Correct!' if result['correct'] else '❌ Incorrect.'}\n\n{result['explanation']}\n\nXP Earned: {result['xp_earned']}"
                
                if result.get("quiz_complete"):
                     response_text += f"\n\n🎉 Quiz Complete!\nScore: {result['score']}/{result['total_questions']}\nTotal XP: {result['total_xp']}"
                     actions = [{"text": "Back to Lessons", "action": "/lesson", "type": "primary"}]
                else:
                    # Next question
                    next_q = await self.quiz_system.get_current_question(session_id)
                    if next_q:
                        response_text += f"\n\nNext Question:\n{next_q.text}"
                        actions = self._build_quiz_options(next_q, session_id)
                    else:
                        actions = [{"text": "Finish", "action": "/lesson", "type": "primary"}]

                return AbstractResponse(text=response_text, actions=actions)

        return AbstractResponse(
            text="Quiz interaction not understood."
        )

    async def start_quiz_for_lesson(self, lesson_id: str, user_id: str) -> AbstractResponse:
        """Helper to start a quiz"""
        lesson = await self.lesson_engine.load_lesson(lesson_id)
        if not lesson:
            return AbstractResponse(text="Lesson not found for quiz.")
            
        # Get questions (handling dict vs object)
        if isinstance(lesson, dict):
             questions_data = lesson.get("quiz", {}).get("questions", [])
        else:
             questions_data = [
                 {"id": q.id, "type": q.type, "text": q.text, "options": q.options, "correct_answer": q.correct_answer} 
                 for q in lesson.quiz_questions
             ]
             
        if not questions_data:
            return AbstractResponse(text="No quiz available for this lesson.")
            
        session_id = self.quiz_system.create_session(user_id, lesson_id, questions_data)
        
        # Get first question
        question = await self.quiz_system.get_current_question(session_id)
        if not question:
             return AbstractResponse(text="Failed to start quiz.")
             
        actions = self._build_quiz_options(question, session_id)
        
        return AbstractResponse(
            text=f"📝 Quiz: {lesson.get('title', lesson_id) if isinstance(lesson, dict) else lesson.title}\n\n{question.text}",
            actions=actions
        )

    def _build_quiz_options(self, question: Any, session_id: str) -> List[Dict]:
        """Helper to build quiz option buttons"""
        actions = []
        if question.type == "multiple_choice":
            for i, opt in enumerate(question.options):
                actions.append({
                    "text": opt["text"],
                    "action": f"quiz:answer:{session_id}:0:{opt['text']}", # Using text as answer for now
                    "type": "secondary"
                })
        elif question.type == "true_false":
            actions.append({"text": "True", "action": f"quiz:answer:{session_id}:0:true", "type": "secondary"})
            actions.append({"text": "False", "action": f"quiz:answer:{session_id}:0:false", "type": "secondary"})
            
        return actions

    async def handle_ai_question(
        self, message: AbstractMessage, session: UserSession, intent: Intent
    ) -> AbstractResponse:
        """Handle AI mentor questions using FIML Narrative Generation Engine"""
        question = intent.data.get("question", "")

        try:
            # Get mentor persona from session preferences (default to Maya)
            mentor_name = (session.preferences or {}).get("mentor", "maya").lower()
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
                lessons_text = "\n\n📚 Related Lessons:\n" + "\n".join(
                    [f"• {lesson}" for lesson in related_lessons]
                )

            formatted_response = (
                f"{mentor_icon} {mentor_name}:\n\n"
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
                text="🤖 AI Mentor:\n\n"
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
                    text="📊 Market Data Query\n\n"
                    "I couldn't identify a specific stock or crypto symbol in your query.\n\n"
                    "Try asking about a specific symbol like:\n"
                    "• 'Show me AAPL price'\n"
                    "• 'What's the price of TSLA stock?'\n"
                    "• 'Tell me about MSFT'\n"
                    "• 'Bitcoin price' or 'BTC price'\n\n"
                    "_Educational purposes only - not financial advice_"
                )

            # Use FIMLEducationalDataAdapter to fetch market data with educational context
            # This now uses full FIML MCP tools integration for real data
            educational_data = await self.fiml_data_adapter.get_educational_snapshot(
                symbol=symbol, user_id=message.user_id, context="mentor"
            )

            # Check if this is fallback data (API not configured)
            is_fallback = educational_data.get("is_fallback", False)
            
            # Format the educational snapshot for display
            formatted_data = await self.fiml_data_adapter.format_for_lesson(educational_data)

            # Use narrative from the educational snapshot (already generated by MCP tools)
            narrative_text = ""
            if educational_data.get("narrative"):
                narrative = educational_data["narrative"]
                # Truncate if needed
                if len(narrative) > MAX_NARRATIVE_SUMMARY_LENGTH:
                    narrative = narrative[:MAX_NARRATIVE_SUMMARY_LENGTH] + "..."
                narrative_text = f"\n\n📝 Educational Insight:\n{narrative}"
            
            # Add key insights if available
            key_insights = educational_data.get("key_insights", [])
            if key_insights and len(key_insights) > 0:
                insights_text = "\n\n💡 Key Insights:\n"
                for insight in key_insights[:3]:  # Limit to 3 insights
                    insights_text += f"• {insight}\n"
                narrative_text += insights_text

            # Build response text
            response_text = f"📊 Market Data for {symbol}\n\n{formatted_data}{narrative_text}"
            
            # Add data source info
            response_text += f"\n\n_Source: {educational_data.get('data_source', 'FIML')}_"
            
            # Add disclaimer
            response_text += f"\n_{educational_data.get('disclaimer', 'Educational purposes only - not financial advice')}_"

            logger.info(
                "Market query response generated",
                user_id=message.user_id,
                symbol=symbol,
                is_fallback=is_fallback,
                has_narrative=bool(educational_data.get("narrative")),
            )

            return AbstractResponse(
                text=response_text,
                metadata={
                    "symbol": symbol,
                    "has_narrative": bool(narrative_text),
                    "is_live_data": not is_fallback,
                    "asset_type": educational_data.get("asset_type", "stock"),
                },
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
                text="📊 Market Data:\n\n"
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

        # Check for explicit symbol mentions
        words = query_upper.split()
        for word in words:
            # Remove common punctuation
            clean_word = word.strip(".,!?$")
            if clean_word in COMMON_SYMBOLS:
                return clean_word

        # Check for company name mentions
        for company_name, symbol in COMPANY_TO_SYMBOL.items():
            if company_name in query_upper:
                return symbol

        # Check for $ prefix (e.g., $AAPL)
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

    async def handle_greeting(
        self, message: AbstractMessage, session: UserSession, intent: Intent
    ) -> AbstractResponse:
        """Handle greetings"""
        return AbstractResponse(
            text="👋 Hello! Welcome to FIML Mobile.\n\n"
            "I'm your AI trading mentor. I can help you:\n"
            "• Learn trading concepts\n"
            "• Analyze market data\n"
            "• Practice with quizzes\n\n"
            "Try asking me:\n"
            "• 'What is a P/E ratio?'\n"
            "• 'Show me AAPL price'\n"
            "• 'Explain risk management'"
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
