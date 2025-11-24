"""
Component 7: Quiz System
Interactive quizzes with scoring and XP rewards
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class QuizQuestion:
    """Quiz question"""
    id: str
    type: str  # multiple_choice, true_false, numeric
    text: str
    options: List[Dict] = None
    correct_answer: Any = None
    explanation: str = ""
    xp_reward: int = 10
    
    def __post_init__(self):
        if self.options is None:
            self.options = []


@dataclass
class QuizSession:
    """Active quiz session"""
    session_id: str
    user_id: str
    lesson_id: str
    questions: List[QuizQuestion]
    current_question_index: int = 0
    answers: Dict[str, Any] = None
    score: int = 0
    total_xp: int = 0
    started_at: datetime = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.answers is None:
            self.answers = {}
        if self.started_at is None:
            self.started_at = datetime.utcnow()


class QuizSystem:
    """
    Manages interactive quizzes
    
    Features:
    - Multiple question types
    - Instant feedback
    - Score calculation
    - XP rewards
    - Progress tracking
    """
    
    def __init__(self):
        self._active_sessions: Dict[str, QuizSession] = {}
        self._completed_sessions: Dict[str, List[QuizSession]] = {}
        logger.info("QuizSystem initialized")
    
    async def start_quiz(
        self,
        user_id: str,
        lesson_id: str,
        questions: List[QuizQuestion]
    ) -> QuizSession:
        """
        Start a new quiz session
        
        Args:
            user_id: User identifier
            lesson_id: Associated lesson
            questions: List of questions
            
        Returns:
            Quiz session
        """
        session_id = f"{user_id}_{lesson_id}_{datetime.utcnow().timestamp()}"
        
        session = QuizSession(
            session_id=session_id,
            user_id=user_id,
            lesson_id=lesson_id,
            questions=questions
        )
        
        self._active_sessions[session_id] = session
        
        logger.info(
            "Quiz started",
            user_id=user_id,
            lesson_id=lesson_id,
            num_questions=len(questions)
        )
        
        return session
    
    async def get_current_question(
        self,
        session_id: str
    ) -> Optional[QuizQuestion]:
        """Get current question for session"""
        session = self._active_sessions.get(session_id)
        if not session:
            return None
        
        if session.current_question_index >= len(session.questions):
            return None
        
        return session.questions[session.current_question_index]
    
    async def submit_answer(
        self,
        session_id: str,
        answer: Any
    ) -> Dict[str, Any]:
        """
        Submit answer for current question
        
        Args:
            session_id: Quiz session ID
            answer: User's answer
            
        Returns:
            Result dict with correct/incorrect, explanation, XP
        """
        session = self._active_sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        
        current_q = await self.get_current_question(session_id)
        if not current_q:
            return {"error": "No current question"}
        
        # Check answer
        is_correct = self._check_answer(current_q, answer)
        
        # Store answer
        session.answers[current_q.id] = {
            "answer": answer,
            "correct": is_correct,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Update score
        if is_correct:
            session.score += 1
            session.total_xp += current_q.xp_reward
        
        # Move to next question
        session.current_question_index += 1
        
        # Check if quiz complete
        quiz_complete = session.current_question_index >= len(session.questions)
        
        if quiz_complete:
            session.completed_at = datetime.utcnow()
            
            # Move to completed
            if session.user_id not in self._completed_sessions:
                self._completed_sessions[session.user_id] = []
            self._completed_sessions[session.user_id].append(session)
            
            # Remove from active
            del self._active_sessions[session_id]
            
            logger.info(
                "Quiz completed",
                user_id=session.user_id,
                score=session.score,
                total_questions=len(session.questions),
                xp_earned=session.total_xp
            )
        
        result = {
            "correct": is_correct,
            "explanation": current_q.explanation if not is_correct else "Correct!",
            "xp_earned": current_q.xp_reward if is_correct else 0,
            "quiz_complete": quiz_complete,
            "score": session.score,
            "total_questions": len(session.questions)
        }
        
        if quiz_complete:
            result["final_score"] = session.score
            result["total_xp"] = session.total_xp
            result["percentage"] = (session.score / len(session.questions)) * 100
        
        return result
    
    def _check_answer(self, question: QuizQuestion, answer: Any) -> bool:
        """Check if answer is correct"""
        if question.type == "multiple_choice":
            # Find correct option
            correct_option = next(
                (opt for opt in question.options if opt.get('correct')),
                None
            )
            if correct_option:
                return answer.lower().strip() == correct_option['text'].lower().strip()
            return str(answer).lower().strip() == str(question.correct_answer).lower().strip()
        
        elif question.type == "true_false":
            answer_lower = str(answer).lower().strip()
            correct_lower = str(question.correct_answer).lower().strip()
            return answer_lower == correct_lower
        
        elif question.type == "numeric":
            try:
                answer_num = float(answer)
                correct_num = float(question.correct_answer)
                # Allow small tolerance for floating point
                return abs(answer_num - correct_num) < 0.01
            except (ValueError, TypeError):
                return False
        
        return False
    
    async def get_session_summary(self, session_id: str) -> Optional[Dict]:
        """Get summary of completed session"""
        # Check active sessions
        if session_id in self._active_sessions:
            session = self._active_sessions[session_id]
            return {
                "status": "in_progress",
                "score": session.score,
                "answered": len(session.answers),
                "total": len(session.questions)
            }
        
        # Check completed sessions
        for user_sessions in self._completed_sessions.values():
            for session in user_sessions:
                if session.session_id == session_id:
                    duration = (session.completed_at - session.started_at).total_seconds()
                    return {
                        "status": "completed",
                        "score": session.score,
                        "total": len(session.questions),
                        "percentage": (session.score / len(session.questions)) * 100,
                        "xp_earned": session.total_xp,
                        "duration_seconds": duration
                    }
        
        return None
    
    async def get_user_quiz_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """Get user's quiz history"""
        if user_id not in self._completed_sessions:
            return []
        
        history = []
        for session in self._completed_sessions[user_id][-limit:]:
            history.append({
                "lesson_id": session.lesson_id,
                "score": session.score,
                "total": len(session.questions),
                "percentage": (session.score / len(session.questions)) * 100,
                "xp_earned": session.total_xp,
                "completed_at": session.completed_at.isoformat() if session.completed_at else None
            })
        
        return history
    
    def format_question(self, question: QuizQuestion) -> str:
        """Format question for display"""
        output = [f"❓ **{question.text}**\n"]
        
        if question.type == "multiple_choice":
            output.append("Choose one:")
            for i, option in enumerate(question.options, 1):
                output.append(f"{i}. {option['text']}")
        
        elif question.type == "true_false":
            output.append("Answer: True or False")
        
        elif question.type == "numeric":
            output.append("Enter a number:")
        
        return "\n".join(output)
