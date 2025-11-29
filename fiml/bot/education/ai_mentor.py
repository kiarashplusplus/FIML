"""
Component 8: AI Mentor Service
Conversational AI mentors with distinct personalities integrated with FIML narrative generation
"""

from enum import Enum
from typing import Dict, List, Optional

import structlog

from fiml.narrative.generator import NarrativeGenerator
from fiml.narrative.models import ExpertiseLevel, Language, NarrativeContext, NarrativePreferences

logger = structlog.get_logger(__name__)


class MentorPersona(Enum):
    """Available mentor personalities"""

    MAYA = "maya"  # Patient guide, uses analogies, fundamentals-focused
    THEO = "theo"  # Analytical, data-driven, technical analysis expert
    ZARA = "zara"  # Psychology-focused, trading discipline, risk mindset


class AIMentorService:
    """
    AI-powered educational mentors with FIML narrative generation

    Features:
    - 3 distinct mentor personas (Maya, Theo, Zara)
    - Integration with FIML narrative generation engine
    - Context-aware responses
    - Educational tone (no advice)
    - Compliance filtering
    - Example-based explanations
    """

    # Mentor personalities
    MENTORS = {
        MentorPersona.MAYA: {
            "name": "Maya",
            "icon": "👩‍🏫",
            "description": "Patient guide who explains concepts with analogies",
            "focus": "Fundamentals and conceptual understanding",
            "style": "patient, uses analogies, beginner-friendly",
            "expertise_level": ExpertiseLevel.BEGINNER,
        },
        MentorPersona.THEO: {
            "name": "Theo",
            "icon": "👨‍💼",
            "description": "Analytical expert focused on data and technical analysis",
            "focus": "Technical analysis and chart patterns",
            "style": "analytical, data-driven, precise",
            "expertise_level": ExpertiseLevel.INTERMEDIATE,
        },
        MentorPersona.ZARA: {
            "name": "Zara",
            "icon": "🧘‍♀️",
            "description": "Psychology coach for trading discipline and mindset",
            "focus": "Trading psychology and risk management",
            "style": "empathetic, mindful, discipline-focused",
            "expertise_level": ExpertiseLevel.BEGINNER,
        },
    }

    def __init__(self, narrative_generator: Optional[NarrativeGenerator] = None):
        """
        Initialize AI mentor service with FIML narrative generator

        Args:
            narrative_generator: FIML narrative generator (creates new if None)
        """
        self.narrative_generator = narrative_generator or NarrativeGenerator()
        # Conversation history per user
        self._conversations: Dict[str, List[Dict]] = {}
        logger.info("AIMentorService initialized with FIML narrative generation")

    def _extract_symbol_from_question(self, question: str) -> Optional[str]:
        """
        Extract stock symbol from user question.

        Args:
            question: User's question text

        Returns:
            Detected stock symbol or 'AAPL' as default
        """
        question_upper = question.upper()

        # Common stock symbols to look for (expandable)
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
        ]

        # Check for explicit mentions
        for symbol in common_symbols:
            if symbol in question_upper.split():
                return symbol

        # Check for company name mentions
        company_map = {
            "APPLE": "AAPL",
            "GOOGLE": "GOOGL",
            "ALPHABET": "GOOGL",
            "MICROSOFT": "MSFT",
            "AMAZON": "AMZN",
            "TESLA": "TSLA",
            "FACEBOOK": "META",
            "META": "META",
            "NVIDIA": "NVDA",
            "NETFLIX": "NFLX",
            "DISNEY": "DIS",
        }

        for company_name, symbol in company_map.items():
            if company_name in question_upper:
                return symbol

        # Default to None if no symbol detected
        return None

    async def respond(
        self,
        user_id: str,
        question: str,
        persona: MentorPersona = MentorPersona.MAYA,
        context: Optional[Dict] = None,
    ) -> Dict:
        """
        Generate mentor response using FIML narrative generation

        Args:
            user_id: User identifier
            question: User's question
            persona: Which mentor to use
            context: Additional context (current lesson, user level, etc.)

        Returns:
            Response dict with text, related_lessons, disclaimer
        """
        mentor = self.MENTORS[persona]

        # Store in conversation history
        if user_id not in self._conversations:
            self._conversations[user_id] = []

        self._conversations[user_id].append(
            {"role": "user", "content": question, "timestamp": "now"}
        )

        try:
            # Extract symbol from question or use provided context
            symbol = (
                context.get("symbol")
                if context and "symbol" in context
                else self._extract_symbol_from_question(question)
            )

            # Generate narrative using FIML engine
            if symbol:
                # Use FIML narrative generation for educational responses
                # Build narrative context from educational question
                narrative_context = NarrativeContext(
                    asset_symbol=symbol,
                    asset_name=(
                        context.get("asset_name", f"{symbol} Stock")
                        if context
                        else f"{symbol} Stock"
                    ),
                    asset_type="stock",
                    market="US",
                    price_data=context.get("price_data", {}) if context else {},
                    preferences=NarrativePreferences(
                        expertise_level=ExpertiseLevel(mentor["expertise_level"]),
                        language=Language.ENGLISH,
                        include_disclaimers=True,
                    ),
                    include_disclaimers=True,
                )

                narrative = await self.narrative_generator.generate_narrative(
                    context=narrative_context
                )
                response_text = self._adapt_narrative_to_persona(
                    narrative.summary, persona, question
                )
            else:
                # General educational response without specific asset context
                response_text = await self._generate_general_response(question, persona)

            logger.info(
                "FIML narrative generated for mentor response",
                user_id=user_id,
                persona=persona.value,
                question_length=len(question),
            )

        except Exception as e:
            # Fallback to template if narrative generation fails
            logger.warning(
                "Failed to generate FIML narrative, using template",
                user_id=user_id,
                persona=persona.value,
                error=str(e),
            )
            response_text = self._generate_template_response(question, persona, context)

        # Add to history
        self._conversations[user_id].append(
            {
                "role": "assistant",
                "persona": persona.value,
                "content": response_text,
                "timestamp": "now",
            }
        )

        # Keep last 10 messages
        self._conversations[user_id] = self._conversations[user_id][-10:]

        logger.info(
            "Mentor response generated",
            user_id=user_id,
            persona=persona.value,
            question_length=len(question),
        )

        return {
            "text": response_text,
            "mentor": mentor["name"],
            "icon": mentor["icon"],
            "related_lessons": self._suggest_lessons(question),
            "disclaimer": "Educational purposes only - not financial advice",
        }

    async def _generate_general_response(self, question: str, persona: MentorPersona) -> str:
        """Generate general educational response using LLM"""
        mentor = self.MENTORS[persona]

        # System prompt based on persona
        system_content = (
            f"You are {mentor['name']}, an AI trading mentor. {mentor['description']}. "
            f"Your style is {mentor['style']}. "
            f"Answer the user's question about trading or finance. "
            "Do not give financial advice. Always be educational. "
            "If the question is not about finance/trading, politely steer back to the topic. "
            "Keep responses concise and helpful.\n\n"
            "IMPORTANT FORMATTING RULES:\n"
            "- Do NOT use markdown formatting (no **, ###, >, ---, etc.)\n"
            "- Use plain text only\n"
            "- Use emojis for visual interest (✅ ❌ 💡 📊 📈 etc.)\n"
            "- Use simple bullet points with • or -\n"
            "- Use line breaks for readability\n"
            "- Keep it conversational and easy to read on mobile"
        )

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": question},
        ]

        try:
            # Access Azure client through narrative generator
            client = self.narrative_generator.azure_client
            if client:
                response = await client.generate_chat_response(messages=messages)
                # Check if response is empty or None
                if response and response.strip():
                    return response
                else:
                    logger.warning("Azure client returned empty response, using template")
                    return self._generate_template_response(question, persona, None)
            else:
                logger.warning("Azure client not available for general response")
                return self._generate_template_response(question, persona, None)

        except Exception as e:
            logger.error("Failed to generate general LLM response", error=str(e))
            return self._generate_template_response(question, persona, None)

    def _adapt_narrative_to_persona(
        self, narrative_text: str, persona: MentorPersona, question: str
    ) -> str:
        """
        Adapt FIML narrative to match mentor persona style

        Args:
            narrative_text: Generated narrative from FIML
            persona: Mentor persona
            question: Original user question

        Returns:
            Adapted response text
        """
        self.MENTORS[persona]

        # Add persona-specific introduction
        intro = ""
        if persona == MentorPersona.MAYA:
            intro = "Great question! Let me explain this in a simple way... "
        elif persona == MentorPersona.THEO:
            intro = "Let's look at the data objectively. "
        elif persona == MentorPersona.ZARA:
            intro = "I appreciate your curiosity. From a mindset perspective, "

        # Combine intro with narrative
        adapted_text = intro + narrative_text

        # Ensure educational disclaimer
        if "for educational purposes" not in adapted_text.lower():
            adapted_text += (
                "\n\n📚 Remember: This is for educational purposes only, not investment advice."
            )

        return adapted_text

    def _generate_template_response(
        self, question: str, persona: MentorPersona, context: Optional[Dict]
    ) -> str:
        """Generate template-based response (placeholder for LLM integration)"""

        mentor = self.MENTORS[persona]
        question_lower = question.lower()

        # P/E Ratio specific response (most common question)
        if (
            "p/e" in question_lower
            or "pe ratio" in question_lower
            or "price to earnings" in question_lower
            or "price-to-earnings" in question_lower
        ):
            if persona == MentorPersona.MAYA:
                return (
                    "Great question! The P/E ratio (Price-to-Earnings ratio) is like a price tag for a company's earnings.\n\n"
                    "Think of it this way: If a stock costs $100 and the company earns $10 per share annually, "
                    "the P/E ratio is 10. This means you're paying $10 for every $1 of earnings.\n\n"
                    "**What it tells you:**\n"
                    "• Low P/E (< 15): Stock might be undervalued or facing challenges\n"
                    "• Medium P/E (15-25): Fairly valued\n"
                    "• High P/E (> 25): Investors expect strong growth\n\n"
                    "Example: If AAPL has a P/E of 28, investors are willing to pay $28 for each $1 of earnings, "
                    "betting on Apple's future growth.\n\n"
                    "💡 Tip: Always compare P/E ratios within the same industry!"
                )

        # Common question patterns
        if any(word in question_lower for word in ["what is", "explain", "how does"]):
            if persona == MentorPersona.MAYA:
                # Extract topic from question for more personalized response
                topic = "this concept"
                if "risk" in question_lower:
                    topic = "risk management"
                elif "stock" in question_lower:
                    topic = "stocks"
                elif "volatility" in question_lower:
                    topic = "volatility"

                return (
                    f"Great question about {topic}! While I'm still learning to provide detailed explanations, "
                    f"I can tell you that this is an important concept in trading and finance.\n\n"
                    f"📚 To learn more, I recommend:\n"
                    f"• Checking out our lessons with /lesson\n"
                    f"• Exploring specific stocks with market data\n"
                    f"• Asking me more specific questions\n\n"
                    f"Try asking: 'What is a P/E ratio?' or 'Show me AAPL price'"
                )

            elif persona == MentorPersona.THEO:
                return (
                    "Let's approach this analytically.\n\n"
                    "While my AI capabilities are being enhanced with FIML's narrative engine, "
                    "I can already help you with market data and analysis.\n\n"
                    "Try:\n"
                    "• /market - View live market data\n"
                    "• Asking about specific stocks (e.g., 'AAPL price')\n"
                    "• /lesson - Learn fundamental concepts"
                )

            else:  # ZARA
                return (
                    "I appreciate your curiosity about trading concepts.\n\n"
                    "Understanding is the first step to confident trading. "
                    "While I'm being integrated with advanced AI capabilities, "
                    "I can already guide you through our structured learning path.\n\n"
                    "Remember: Knowledge reduces anxiety. Start with /lesson to build a solid foundation."
                )

        # Default response
        return (
            f"{mentor['icon']} {mentor['name']} here!\n\n"
            f"I understand you're asking about: _{question}_\n\n"
            f"I'm here to help you learn! While my AI capabilities are being enhanced, "
            f"you can already:\n"
            f"• Browse lessons with /lesson\n"
            f"• Check live market data\n"
            f"• Ask about specific trading concepts\n\n"
            f"Try asking: 'What is a P/E ratio?' or 'Show me AAPL price'"
        )

    def _suggest_lessons(self, question: str) -> List[str]:
        """Suggest relevant lessons based on question"""
        question_lower = question.lower()
        suggestions = []

        if any(word in question_lower for word in ["price", "stock", "bid", "ask"]):
            suggestions.append("stock_basics_001")

        if any(word in question_lower for word in ["risk", "loss", "protect"]):
            suggestions.append("risk_management_101")

        if any(word in question_lower for word in ["chart", "technical", "pattern"]):
            suggestions.append("technical_analysis_intro")

        return suggestions

    async def get_conversation_history(self, user_id: str, limit: int = 5) -> List[Dict]:
        """Get recent conversation history"""
        if user_id not in self._conversations:
            return []

        return self._conversations[user_id][-limit:]

    def get_mentor_info(self, persona: MentorPersona) -> Dict:
        """Get information about a mentor"""
        return self.MENTORS[persona]

    def list_mentors(self) -> List[Dict]:
        """List all available mentors"""
        return [{"persona": persona.value, **info} for persona, info in self.MENTORS.items()]
