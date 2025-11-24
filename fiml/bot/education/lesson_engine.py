"""
Component 6: Lesson Content Engine
Renders lessons with live FIML market data
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
import yaml

logger = structlog.get_logger(__name__)


@dataclass
class LessonSection:
    """A section within a lesson"""
    type: str  # introduction, live_example, explanation, chart, key_takeaways
    content: str
    fiml_query: Optional[Dict] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class QuizQuestion:
    """A quiz question"""
    id: str
    type: str  # multiple_choice, true_false, numeric
    text: str
    options: List[Dict]
    correct_answer: Any
    xp_reward: int = 10


@dataclass
class Lesson:
    """Complete lesson structure"""
    id: str
    title: str
    category: str
    difficulty: str
    duration_minutes: int
    learning_objectives: List[str]
    prerequisites: List[str]
    sections: List[LessonSection]
    quiz_questions: List[QuizQuestion]
    xp_reward: int
    next_lesson: Optional[str]

    def __post_init__(self):
        if not isinstance(self.sections, list):
            self.sections = []
        if not isinstance(self.quiz_questions, list):
            self.quiz_questions = []


class LessonContentEngine:
    """
    Manages and renders educational lessons

    Features:
    - YAML lesson loading
    - Dynamic rendering with live FIML data
    - Progress tracking
    - Prerequisite checking
    """

    def __init__(self, lessons_path: str = "./fiml/bot/content/lessons"):
        """
        Initialize lesson engine

        Args:
            lessons_path: Path to lessons directory
        """
        self.lessons_path = Path(lessons_path)
        self._lessons_cache: Dict[str, Lesson] = {}
        self._user_progress: Dict[str, Dict] = {}  # user_id -> progress

        logger.info("LessonContentEngine initialized", path=lessons_path)

    async def load_lesson(self, lesson_id: str) -> Optional[Lesson]:
        """
        Load lesson from YAML file

        Args:
            lesson_id: Lesson identifier

        Returns:
            Lesson object or None
        """
        # Check cache
        if lesson_id in self._lessons_cache:
            return self._lessons_cache[lesson_id]

        # Load from file
        lesson_file = self.lessons_path / f"{lesson_id}.yaml"

        if not lesson_file.exists():
            logger.warning("Lesson file not found", lesson_id=lesson_id)
            return None

        try:
            with open(lesson_file, 'r') as f:
                lesson_data = yaml.safe_load(f)

            # Parse sections
            sections = []
            for section_data in lesson_data.get('sections', []):
                sections.append(LessonSection(
                    type=section_data['type'],
                    content=section_data.get('content', ''),
                    fiml_query=section_data.get('fiml_query'),
                    metadata=section_data.get('metadata', {})
                ))

            # Parse quiz questions
            quiz_questions = []
            for q_data in lesson_data.get('quiz', {}).get('questions', []):
                quiz_questions.append(QuizQuestion(
                    id=q_data['id'],
                    type=q_data['type'],
                    text=q_data['text'],
                    options=q_data.get('options', []),
                    correct_answer=q_data.get('correct_answer'),
                    xp_reward=q_data.get('xp_reward', 10)
                ))

            # Create lesson
            lesson = Lesson(
                id=lesson_id,
                title=lesson_data['title'],
                category=lesson_data.get('category', 'general'),
                difficulty=lesson_data.get('difficulty', 'beginner'),
                duration_minutes=lesson_data.get('duration_minutes', 5),
                learning_objectives=lesson_data.get('learning_objectives', []),
                prerequisites=lesson_data.get('prerequisites', []),
                sections=sections,
                quiz_questions=quiz_questions,
                xp_reward=lesson_data.get('xp_reward', 50),
                next_lesson=lesson_data.get('next_lesson')
            )

            # Cache it
            self._lessons_cache[lesson_id] = lesson

            logger.info("Lesson loaded", lesson_id=lesson_id, sections=len(sections))
            return lesson

        except Exception as e:
            logger.error("Failed to load lesson", lesson_id=lesson_id, error=str(e))
            return None

    async def render_lesson(
        self,
        lesson: Lesson,
        user_id: str,
        include_fiml_data: bool = True
    ) -> str:
        """
        Render lesson with live data

        Args:
            lesson: Lesson to render
            user_id: User identifier
            include_fiml_data: Whether to fetch live FIML data

        Returns:
            Rendered lesson text
        """
        output = []

        # Header
        output.append(f"📚 **{lesson.title}**\n")
        output.append(f"⏱️ {lesson.duration_minutes} minutes | "
                     f"📊 {lesson.difficulty.title()}\n")

        # Learning objectives
        if lesson.learning_objectives:
            output.append("\n**Learning Objectives:**")
            for obj in lesson.learning_objectives:
                output.append(f"• {obj}")
            output.append("")

        # Render sections
        for section in lesson.sections:
            if section.type == "introduction":
                output.append(section.content)
                output.append("")

            elif section.type == "live_example":
                output.append("📊 **Live Example:**")

                if include_fiml_data and section.fiml_query:
                    # Placeholder for FIML data
                    output.append("\n_[Live market data would appear here]_")
                    output.append(f"_Query: {section.fiml_query.get('symbol', 'N/A')}_\n")

                output.append(section.content)
                output.append("")

            elif section.type == "explanation":
                output.append(section.content)
                output.append("")

            elif section.type == "chart":
                output.append("📈 **Chart:**")
                output.append("_[Chart would be generated here]_\n")
                output.append(section.content)
                output.append("")

            elif section.type == "key_takeaways":
                output.append("🔑 **Key Takeaways:**")
                # Parse content as bullet points
                for line in section.content.split('\n'):
                    if line.strip():
                        output.append(f"• {line.strip()}")
                output.append("")

        # Footer
        output.append(f"✨ Complete this lesson to earn **{lesson.xp_reward} XP**")

        if lesson.quiz_questions:
            output.append(f"📝 Quiz: {len(lesson.quiz_questions)} questions")

        return "\n".join(output)

    async def check_prerequisites(
        self,
        user_id: str,
        lesson: Lesson
    ) -> tuple[bool, List[str]]:
        """
        Check if user meets lesson prerequisites

        Args:
            user_id: User identifier
            lesson: Lesson to check

        Returns:
            (prerequisites_met, missing_lessons)
        """
        if not lesson.prerequisites:
            return True, []

        user_progress = self._user_progress.get(user_id, {})
        completed = user_progress.get('completed', set())

        missing = [
            prereq for prereq in lesson.prerequisites
            if prereq not in completed
        ]

        return len(missing) == 0, missing

    async def mark_completed(self, user_id: str, lesson_id: str):
        """Mark lesson as completed for user"""
        if user_id not in self._user_progress:
            self._user_progress[user_id] = {
                'completed': set(),
                'in_progress': set()
            }

        self._user_progress[user_id]['completed'].add(lesson_id)
        if lesson_id in self._user_progress[user_id]['in_progress']:
            self._user_progress[user_id]['in_progress'].remove(lesson_id)

        logger.info("Lesson completed", user_id=user_id, lesson_id=lesson_id)

    async def get_next_lesson(self, user_id: str, current_lesson_id: str) -> Optional[str]:
        """Get next recommended lesson"""
        current = await self.load_lesson(current_lesson_id)
        if current and current.next_lesson:
            return current.next_lesson
        return None

    async def get_user_progress(self, user_id: str) -> Dict:
        """Get user's learning progress"""
        return self._user_progress.get(user_id, {
            'completed': set(),
            'in_progress': set()
        })

    def create_sample_lesson(self, lesson_id: str = "stock_basics_001"):
        """Create a sample lesson for demonstration"""
        sample = {
            'id': lesson_id,
            'title': 'Understanding Stock Prices',
            'category': 'foundations',
            'difficulty': 'beginner',
            'duration_minutes': 5,
            'learning_objectives': [
                'Understand bid-ask spread',
                'Read price charts',
                'Interpret volume data'
            ],
            'prerequisites': [],
            'sections': [
                {
                    'type': 'introduction',
                    'content': 'Every second, millions of stock trades happen worldwide. '
                              'Let\'s explore what makes prices move using real market data!'
                },
                {
                    'type': 'live_example',
                    'content': 'Notice the bid and ask prices above? The bid is what buyers are '
                              'willing to pay, the ask is what sellers want. The difference is the spread.',
                    'fiml_query': {
                        'symbol': 'AAPL',
                        'market': 'US'
                    }
                },
                {
                    'type': 'explanation',
                    'content': 'The **spread** is the market\'s transaction cost. In liquid stocks '
                              'like AAPL, it\'s tiny (often $0.01). In less liquid stocks, it can be much wider.'
                },
                {
                    'type': 'key_takeaways',
                    'content': 'Bid-ask spread = transaction cost\n'
                              'Liquid stocks have narrow spreads\n'
                              'Volume indicates market interest'
                }
            ],
            'quiz': {
                'questions': [
                    {
                        'id': 'q1',
                        'type': 'multiple_choice',
                        'text': 'If Bid=$100 and Ask=$100.05, what is the spread?',
                        'options': [
                            {'text': '$0.05', 'correct': True},
                            {'text': '$100', 'correct': False},
                            {'text': '$200.05', 'correct': False}
                        ],
                        'correct_answer': '$0.05',
                        'xp_reward': 10
                    }
                ]
            },
            'xp_reward': 50,
            'next_lesson': 'stock_basics_002'
        }

        # Save to file
        self.lessons_path.mkdir(parents=True, exist_ok=True)
        lesson_file = self.lessons_path / f"{lesson_id}.yaml"

        with open(lesson_file, 'w') as f:
            yaml.dump(sample, f, default_flow_style=False)

        logger.info("Sample lesson created", lesson_id=lesson_id)
        return lesson_file
