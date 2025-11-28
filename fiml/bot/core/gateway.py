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
    FK_DSL_QUERY = "fk_dsl_query"
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
    AWAITING_KEY_INPUT = "awaiting_key_input"
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
        "/fkdsl",
        "/dsl",
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

    # FK-DSL keywords - queries that should be routed to DSL execution
    DSL_KEYWORDS = ["evaluate", "compare", "correlate", "analyze", "trend", "volatility"]

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
        context_action = (message.context or {}).get("action", "")
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

        # Check for FK-DSL query patterns (high priority)
        # DSL queries typically start with EVALUATE, COMPARE, CORRELATE, etc.
        if self._is_dsl_query(text):
            return Intent(
                type=IntentType.FK_DSL_QUERY, data={"query": message.text}, confidence=0.9
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

    def _is_dsl_query(self, text: str) -> bool:
        """
        Check if text is a FK-DSL query.

        FK-DSL queries typically start with uppercase keywords like:
        - EVALUATE TSLA: PRICE, VOLATILITY(30d)
        - COMPARE AAPL, MSFT: PE_RATIO, MARKET_CAP
        - CORRELATE BTC, ETH: PRICE(90d)
        """
        text_upper = text.upper().strip()

        # Check for DSL command prefixes
        dsl_prefixes = ["EVALUATE", "COMPARE", "CORRELATE", "ANALYZE", "TREND", "SCREEN"]
        if any(text_upper.startswith(prefix) for prefix in dsl_prefixes):
            return True

        # Check for DSL syntax patterns (colon after symbol, parentheses for timeframes)
        import re
        dsl_pattern = r"^[A-Z]+\s+[A-Z0-9,\s]+:\s*[A-Z_,\s\(\)0-9d]+$"
        if re.match(dsl_pattern, text_upper):
            return True

        return False


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
            IntentType.FK_DSL_QUERY: self.handle_fk_dsl_query,
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
                text="📚 Available Commands:\n\n"
                     "📖 /lesson - Browse lessons\n"
                     "📊 /progress - View your progress\n"
                     "🏆 /leaderboard - See top learners\n"
                     "🧠 /quiz - Take a quiz\n"
                     "💬 /mentor - Talk to AI mentor\n"
                     "🔑 /addkey - Add API keys\n"
                     "📈 /fkdsl - Execute FK-DSL queries\n\n"
                     "Or just ask me anything about markets or trading!",
                actions=[
                    {"text": "Start Lesson", "action": "/lesson", "type": "primary"},
                    {"text": "View Progress", "action": "/progress", "type": "secondary"},
                ]
            )

        elif command == "/cancel":
            # Cancel any ongoing operation
            if session.state == SessionState.AWAITING_KEY_INPUT:
                session.state = SessionState.IDLE
                if "awaiting_key_for" in session.metadata:
                    session.metadata.pop("awaiting_key_for")
                return AbstractResponse(
                    text="✅ Key addition cancelled.\n\n"
                         "Use /addkey when you're ready to add API keys.",
                    actions=[
                        {"text": "Add Key", "action": "/addkey", "type": "primary"},
                        {"text": "Help", "action": "/help", "type": "secondary"}
                    ]
                )
            else:
                return AbstractResponse(
                    text="Nothing to cancel. How can I help you?",
                    actions=[
                        {"text": "Help", "action": "/help", "type": "primary"}
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
                     "Ask me anything about trading, markets, or financial concepts.\n",
                actions=[]
            )

        # Check for provider-specific addkey (e.g., /addkey:binance)
        elif command.startswith("/addkey:"):
            provider = command.split(":")[-1].lower()
            
            # Validate provider exists
            provider_info = self.key_manager.get_provider_info(provider)
            if not provider_info:
                return AbstractResponse(
                    text=f"❌ Unknown provider: {provider}\n\n"
                         f"Supported providers: binance, coinbase, alphavantage, polygon, finnhub, fmp"
                )
            
            # Update session to await key input
            session.state = SessionState.AWAITING_KEY_INPUT
            if session.metadata is None:
                session.metadata = {}
            session.metadata["awaiting_key_for"] = provider
            
            # Determine if secret is needed
            needs_secret = provider in ["binance", "coinbase", "kraken"]
            
            if needs_secret:
                instructions = (
                    f"🔑 Setting up {provider_info['name']}\n\n"
                    f"Please send your API Key and Secret in this format:\n"
                    f"`KEY SECRET`\n\n"
                    f"Example: `abc123xyz def456uvw`\n\n"
                    f"⚠️ Make sure to include both the key and secret separated by a space."
                )
            else:
                instructions = (
                    f"🔑 Setting up {provider_info['name']}\n\n"
                    f"Please send your API Key:\n\n"
                    f"Just paste your key in the next message."
                )
            
            return AbstractResponse(
                text=instructions,
                actions=[
                    {"text": "Cancel", "action": "/cancel", "type": "secondary"}
                ]
            )

        elif command == "/addkey":
            # Platform-aware response
            is_mobile = message.platform in ("mobile", "expo", "app")
            
            if is_mobile:
                # Mobile users: direct to Home tab dashboard
                return AbstractResponse(
                    text="🔑 API Key Management\n\n"
                         "Head to your **Home** tab to manage API keys visually!\n\n"
                         "You can:\n"
                         "✓ View all providers at a glance\n"
                         "✓ Add keys with a simple form\n"
                         "✓ Test connections instantly\n"
                         "✓ Remove keys securely\n\n"
                         "Or select a provider below:",
                    actions=[
                        {"text": "Binance", "action": "/addkey:binance", "type": "secondary"},
                        {"text": "Coinbase", "action": "/addkey:coinbase", "type": "secondary"},
                        {"text": "Alpha Vantage", "action": "/addkey:alphavantage", "type": "secondary"},
                        {"text": "Go to Home", "action": "navigate:home", "type": "primary"},
                    ]
                )
            else:
                # Telegram users: command-based instructions
                return AbstractResponse(
                    text="🔑 Add API Key\n\n"
                         "To add an API key, use:\n"
                         "`/addkey <provider> <api_key> [api_secret]`\n\n"
                         "Example:\n"
                         "`/addkey binance abc123xyz`\n\n"
                         "Or select a provider:",
                    actions=[
                        {"text": "Binance", "action": "/addkey:binance", "type": "secondary"},
                        {"text": "Coinbase", "action": "/addkey:coinbase", "type": "secondary"},
                        {"text": "Alpha Vantage", "action": "/addkey:alphavantage", "type": "secondary"},
                        {"text": "Help", "action": "/help", "type": "primary"},
                    ]
                )


        elif command == "/progress":
             progress = await self.lesson_engine.get_user_progress(message.user_id)
             completed = len((progress or {}).get("completed", []))
             return AbstractResponse(
                text=f"📈 Your Progress\n\n"
                     f"Lessons Completed: {completed}\n"
                     f"Current Streak: {(session.metadata or {}).get('streak', 0)} days\n"
                     f"Total XP: {(session.metadata or {}).get('xp', 0)}",
                actions=[{"text": "Continue Learning", "action": "/lesson", "type": "primary"}]
            )

        elif command in ("/fkdsl", "/dsl"):
            return await self._show_fkdsl_help()

        return AbstractResponse(
            text=f"Command {command} is not fully implemented on mobile yet.",
            metadata={"handled_by": "gateway_fallback"},
        )

    async def handle_lesson_request(
        self, message: AbstractMessage, session: UserSession, intent: Intent
    ) -> AbstractResponse:
        """Handle lesson requests with dynamic lesson loading from content directory"""
        # Dynamically load lessons from the lesson engine
        lessons = await self.lesson_engine.list_lessons()

        if not lessons:
            # Fallback if no lessons found
            return AbstractResponse(
                text="📚 No lessons available yet.\n\n"
                     "The lesson content is being prepared. Please check back later!",
                actions=[]
            )

        actions = []
        for lesson in lessons:
            difficulty_badge = {
                "beginner": "🟢",
                "intermediate": "🟡",
                "advanced": "🔴"
            }.get(lesson.get("difficulty", "beginner"), "⚪")

            actions.append({
                "text": f"{difficulty_badge} {lesson['title']}",
                "action": f"lesson:start:{lesson['id']}",
                "type": "secondary"
            })

        return AbstractResponse(
            text=f"📚 Available Lessons ({len(lessons)} total)\n\n"
                 "🟢 Beginner | 🟡 Intermediate | 🔴 Advanced\n\n"
                 "Select a lesson to start learning:",
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
            text=f"📝 Quiz: {lesson.get('title', lesson_id) if isinstance(lesson, dict) else getattr(lesson, 'title', lesson_id)}\n\n{question.text}",
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
        """
        Handle general AI mentor questions (any question not matching other intents)
        Uses AIMentorService with proper FIML integration for market data
        """
        # Check if waiting for key input
        if session.state == SessionState.AWAITING_KEY_INPUT:
            provider = session.metadata.get("awaiting_key_for")
            
            if not provider:
                # Reset state if no provider set
                session.state = SessionState.IDLE
                return AbstractResponse(
                    text="❌ Session error. Please try /addkey again."
                )
            
            # Parse key input
            parts = message.text.strip().split()
            api_key = parts[0] if len(parts) > 0 else ""
            api_secret = parts[1] if len(parts) > 1 else None
            
            if not api_key:
                return AbstractResponse(
                    text="❌ No API key provided. Please send your API key or use /cancel to exit.",
                    actions=[
                        {"text": "Cancel", "action": "/cancel", "type": "secondary"}
                    ]
                )
            
            # Attempt to store
            try:
                success = await self.key_manager.store_user_key(
                    user_id=message.user_id,
                    provider=provider,
                    api_key=api_key,
                    metadata={
                        "added_via": "chat",
                        "added_at": datetime.now(UTC).isoformat(),
                        "api_secret": api_secret if api_secret else None
                    }
                )
                
                if success:
                    # Reset session state
                    session.state = SessionState.IDLE
                    if "awaiting_key_for" in session.metadata:
                        session.metadata.pop("awaiting_key_for")
                    
                    return AbstractResponse(
                        text=f"✅ {provider.capitalize()} API key added successfully!\n\n"
                             f"Use /testkey to verify it works, or add more providers with /addkey.",
                        actions=[
                            {"text": "Test Key", "action": f"/testkey:{provider}", "type": "primary"},
                            {"text": "Add Another", "action": "/addkey", "type": "secondary"}
                        ]
                    )
                else:
                    return AbstractResponse(
                        text="❌ Failed to store API key. Please check the format and try again.",
                        actions=[
                            {"text": "Retry", "action": f"/addkey:{provider}", "type": "primary"},
                            {"text": "Cancel", "action": "/cancel", "type": "secondary"}
                        ]
                    )
            
            except Exception as e:
                logger.error("Error storing key", user_id=message.user_id, error=str(e))
                session.state = SessionState.IDLE
                return AbstractResponse(
                    text=f"❌ Error: {str(e)}",
                    actions=[{"text": "Try Again", "action": "/addkey", "type": "primary"}]
                )

        question = intent.data.get("question", message.text)

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

    async def _show_fkdsl_help(self) -> AbstractResponse:
        """Show FK-DSL help and example queries"""
        return AbstractResponse(
            text="🔮 Financial Knowledge DSL (FK-DSL)\n\n"
                 "FK-DSL lets you run advanced financial analysis queries.\n\n"
                 "📝 Example Queries:\n"
                 "• `EVALUATE TSLA: PRICE, VOLATILITY(30d)`\n"
                 "• `COMPARE AAPL, MSFT: PE_RATIO, MARKET_CAP`\n"
                 "• `CORRELATE BTC, ETH: PRICE(90d)`\n"
                 "• `SCREEN SECTOR=TECH: PE_RATIO < 30`\n\n"
                 "💡 Tips:\n"
                 "• Use uppercase for commands (EVALUATE, COMPARE, etc.)\n"
                 "• Separate metrics with commas\n"
                 "• Add timeframes in parentheses: (30d), (1y)\n\n"
                 "_Type a query to execute it!_",
            actions=[
                {"text": "EVALUATE AAPL: PRICE", "action": "dsl:EVALUATE AAPL: PRICE, VOLUME", "type": "primary"},
                {"text": "COMPARE TSLA, NVDA", "action": "dsl:COMPARE TSLA, NVDA: PE_RATIO", "type": "secondary"},
                {"text": "CORRELATE BTC, ETH", "action": "dsl:CORRELATE BTC, ETH: PRICE(30d)", "type": "secondary"},
            ],
            metadata={"intent": "fk_dsl_help"},
        )

    async def handle_fk_dsl_query(
        self, message: AbstractMessage, session: UserSession, intent: Intent
    ) -> AbstractResponse:
        """
        Handle FK-DSL query execution.

        This method provides a unified interface for executing FK-DSL queries
        across both Telegram bot and mobile app.
        """
        from fiml.mcp.tools import execute_fk_dsl

        query = intent.data.get("query", "")

        # Check if this is a DSL action from button press
        if query.startswith("dsl:"):
            query = query[4:]  # Remove "dsl:" prefix

        if not query.strip():
            return await self._show_fkdsl_help()

        try:
            logger.info(
                "Executing FK-DSL query",
                user_id=message.user_id,
                query=query,
            )

            # Execute the DSL query synchronously for immediate response
            result = await execute_fk_dsl(query=query, async_execution=False)

            if result.get("status") == "failed":
                return AbstractResponse(
                    text=f"❌ DSL Query Failed\n\n"
                         f"Query: `{query}`\n\n"
                         f"Error: {result.get('error', 'Unknown error')}\n\n"
                         "Try /fkdsl for examples and syntax help.",
                    metadata={"status": "error", "query": query},
                )

            # Format successful result
            formatted_result = self._format_dsl_result(query, result)

            return AbstractResponse(
                text=formatted_result,
                metadata={
                    "status": "success",
                    "query": query,
                    "intent": "fk_dsl_query",
                },
                actions=[
                    {"text": "Run Another Query", "action": "/fkdsl", "type": "secondary"},
                ],
            )

        except Exception as e:
            logger.error(
                "FK-DSL execution error",
                user_id=message.user_id,
                query=query,
                error=str(e),
            )

            return AbstractResponse(
                text=f"❌ Error executing query\n\n"
                     f"Query: `{query}`\n"
                     f"Error: {str(e)}\n\n"
                     "Try /fkdsl for syntax help and examples.",
                metadata={"status": "error", "query": query},
            )

    def _format_dsl_result(self, query: str, result: dict) -> str:
        """Format DSL execution result for display"""
        output = ["🔮 FK-DSL Query Result\n"]
        output.append(f"Query: `{query}`\n")

        if result.get("status") == "completed":
            data = result.get("result", {})

            # Handle different result types
            if isinstance(data, dict):
                if "symbols" in data:
                    # Multi-symbol result
                    for symbol, metrics in data.get("data", {}).items():
                        output.append(f"\n📊 **{symbol}**")
                        if isinstance(metrics, dict):
                            for key, value in metrics.items():
                                output.append(f"  • {key}: {self._format_value(value)}")
                elif "comparison" in data:
                    # Comparison result
                    output.append("\n📈 Comparison:")
                    for item in data.get("comparison", []):
                        output.append(f"  • {item}")
                elif "correlation" in data:
                    # Correlation result
                    corr = data.get("correlation", {})
                    output.append(f"\n🔗 Correlation: {corr.get('value', 'N/A')}")
                    output.append(f"   Period: {corr.get('period', 'N/A')}")
                else:
                    # Generic dict result
                    for key, value in data.items():
                        output.append(f"• {key}: {self._format_value(value)}")
            else:
                output.append(f"\n{data}")

        output.append("\n_Educational purposes only - not financial advice_")
        return "\n".join(output)

    def _format_value(self, value: Any) -> str:
        """Format a value for display"""
        if isinstance(value, float):
            if abs(value) >= 1_000_000_000:
                return f"${value/1_000_000_000:.2f}B"
            elif abs(value) >= 1_000_000:
                return f"${value/1_000_000:.2f}M"
            elif abs(value) < 0.01:
                return f"{value:.6f}"
            else:
                return f"{value:.2f}"
        elif isinstance(value, int):
            return f"{value:,}"
        else:
            return str(value)

    def register_handler(self, intent_type: IntentType, handler: Any) -> None:
        """Register custom handler for intent type"""
        self.handlers[intent_type] = handler
        logger.info("Handler registered", intent_type=intent_type.value)
