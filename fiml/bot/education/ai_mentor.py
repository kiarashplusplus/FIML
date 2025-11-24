"""
Component 8: AI Mentor Service
Conversational AI mentors with distinct personalities integrated with FIML narrative generation
"""

from typing import Dict, List, Optional
from enum import Enum
import structlog
from fiml.narrative.generator import NarrativeGenerator
from fiml.narrative.models import (
    ExpertiseLevel,
    NarrativeContext,
    NarrativePreferences,
    NarrativeType
)

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
            "expertise_level": ExpertiseLevel.BEGINNER
        },
        MentorPersona.THEO: {
            "name": "Theo",
            "icon": "👨‍💼",
            "description": "Analytical expert focused on data and technical analysis",
            "focus": "Technical analysis and chart patterns",
            "style": "analytical, data-driven, precise",
            "expertise_level": ExpertiseLevel.INTERMEDIATE
        },
        MentorPersona.ZARA: {
            "name": "Zara",
            "icon": "🧘‍♀️",
            "description": "Psychology coach for trading discipline and mindset",
            "focus": "Trading psychology and risk management",
            "style": "empathetic, mindful, discipline-focused",
            "expertise_level": ExpertiseLevel.BEGINNER
        }
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
    
    async def respond(
        self,
        user_id: str,
        question: str,
        persona: MentorPersona = MentorPersona.MAYA,
        context: Optional[Dict] = None
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
        
        self._conversations[user_id].append({
            "role": "user",
            "content": question,
            "timestamp": "now"
        })
        
        try:
            # Use FIML narrative generation for educational responses
            # Build narrative context from educational question
            narrative_context = NarrativeContext(
                asset_symbol=context.get("symbol", "AAPL") if context else "AAPL",
                asset_name=context.get("asset_name", "Example Stock") if context else "Example Stock",
                asset_type="stock",
                market="US",
                price_data=context.get("price_data", {}) if context else {},
                preferences=NarrativePreferences(
                    expertise_level=mentor["expertise_level"],
                    language="en",
                    tone="educational",
                    include_disclaimers=True
                ),
                include_disclaimers=True
            )
            
            # Generate narrative using FIML engine
            narrative = await self.narrative_generator.generate_narrative(
                context=narrative_context
            )
            
            # Adapt narrative to mentor persona style
            response_text = self._adapt_narrative_to_persona(
                narrative.full_text,
                persona,
                question
            )
            
            logger.info(
                "FIML narrative generated for mentor response",
                user_id=user_id,
                persona=persona.value,
                question_length=len(question)
            )
            
        except Exception as e:
            # Fallback to template if narrative generation fails
            logger.warning(
                "Failed to generate FIML narrative, using template",
                user_id=user_id,
                persona=persona.value,
                error=str(e)
            )
            response_text = self._generate_template_response(
                question, persona, context
            )
        
        # Add to history
        self._conversations[user_id].append({
            "role": "assistant",
            "persona": persona.value,
            "content": response_text,
            "timestamp": "now"
        })
        
        # Keep last 10 messages
        self._conversations[user_id] = self._conversations[user_id][-10:]
        
        logger.info(
            "Mentor response generated",
            user_id=user_id,
            persona=persona.value,
            question_length=len(question)
        )
        
        return {
            "text": response_text,
            "mentor": mentor["name"],
            "icon": mentor["icon"],
            "related_lessons": self._suggest_lessons(question),
            "disclaimer": "Educational purposes only - not financial advice"
        }
    
    def _adapt_narrative_to_persona(
        self,
        narrative_text: str,
        persona: MentorPersona,
        question: str
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
        mentor = self.MENTORS[persona]
        
        # Add persona-specific introduction
        intro = ""
        if persona == MentorPersona.MAYA:
            intro = f"Great question! Let me explain this in a simple way... "
        elif persona == MentorPersona.THEO:
            intro = f"Let's look at the data objectively. "
        elif persona == MentorPersona.ZARA:
            intro = f"I appreciate your curiosity. From a mindset perspective, "
        
        # Combine intro with narrative
        adapted_text = intro + narrative_text
        
        # Ensure educational disclaimer
        if "for educational purposes" not in adapted_text.lower():
            adapted_text += "\n\n📚 Remember: This is for educational purposes only, not investment advice."
        
        return adapted_text
    
    def _generate_template_response(
        self,
        question: str,
        persona: MentorPersona,
        context: Optional[Dict]
    ) -> str:
        """Generate template-based response (placeholder for LLM integration)"""
        
        mentor = self.MENTORS[persona]
        question_lower = question.lower()
        
        # Common question patterns
        if any(word in question_lower for word in ["what is", "explain", "how does"]):
            if persona == MentorPersona.MAYA:
                return (
                    f"{mentor['icon']} **Maya here!**\n\n"
                    f"Great question! Let me explain this in a simple way.\n\n"
                    f"Think of it like this: [concept explanation would go here]\n\n"
                    f"Want to see a real example? Try the relevant lesson!\n\n"
                    f"_Note: This is educational information only._"
                )
            
            elif persona == MentorPersona.THEO:
                return (
                    f"{mentor['icon']} **Theo here.**\n\n"
                    f"Let's look at the data.\n\n"
                    f"[Analytical explanation with numbers would go here]\n\n"
                    f"The key metrics to watch are: [list]\n\n"
                    f"_Educational purposes only - not advice._"
                )
            
            else:  # ZARA
                return (
                    f"{mentor['icon']} **Zara here.**\n\n"
                    f"That's an important question about mindset.\n\n"
                    f"From a psychological perspective: [insight would go here]\n\n"
                    f"Remember: discipline beats emotion in trading.\n\n"
                    f"_Not financial advice - for learning only._"
                )
        
        # Default response
        return (
            f"{mentor['icon']} **{mentor['name']} here!**\n\n"
            f"I understand you're asking about: _{question}_\n\n"
            f"This is a great topic! The AI mentor system is being integrated with "
            f"FIML's narrative generation engine. Soon I'll be able to:\n"
            f"• Answer questions with real market examples\n"
            f"• Explain concepts in my unique style\n"
            f"• Guide you through lessons interactively\n\n"
            f"For now, check out:\n"
            f"/lesson - Browse available lessons\n"
            f"/help - See what I can help with\n\n"
            f"_Educational purposes only - not financial advice_"
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
    
    async def get_conversation_history(
        self,
        user_id: str,
        limit: int = 5
    ) -> List[Dict]:
        """Get recent conversation history"""
        if user_id not in self._conversations:
            return []
        
        return self._conversations[user_id][-limit:]
    
    def get_mentor_info(self, persona: MentorPersona) -> Dict:
        """Get information about a mentor"""
        return self.MENTORS[persona]
    
    def list_mentors(self) -> List[Dict]:
        """List all available mentors"""
        return [
            {
                "persona": persona.value,
                **info
            }
            for persona, info in self.MENTORS.items()
        ]
