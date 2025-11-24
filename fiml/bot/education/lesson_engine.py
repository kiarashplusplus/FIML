"""
Component 6: Lesson Content Engine
Renders lessons with live FIML market data
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

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

    async def load_lesson(self, lesson_id: str) -> Optional[Dict]:
        """
        Load lesson from YAML file

        Args:
            lesson_id: Lesson identifier

        Returns:
            Lesson dict or None
        """
        # Check cache
        if lesson_id in self._lessons_cache:
            cached = self._lessons_cache[lesson_id]
            # Convert to dict for API compatibility
            return self._lesson_to_dict(cached)

        # Load from file
        lesson_file = self.lessons_path / f"{lesson_id}.yaml"

        if not lesson_file.exists():
            logger.warning("Lesson file not found", lesson_id=lesson_id)
            return None

        try:
            with open(lesson_file, "r") as f:
                lesson_data = yaml.safe_load(f)

            # Parse sections
            sections = []
            for section_data in lesson_data.get("sections", []):
                sections.append(
                    LessonSection(
                        type=section_data["type"],
                        content=section_data.get("content", ""),
                        fiml_query=section_data.get("fiml_query"),
                        metadata=section_data.get("metadata", {}),
                    )
                )

            # Parse quiz questions
            quiz_questions = []
            for idx, q_data in enumerate(lesson_data.get("quiz", {}).get("questions", [])):
                # Generate ID if not provided
                question_id = q_data.get("id", f"{lesson_id}_q{idx + 1}")
                quiz_questions.append(
                    QuizQuestion(
                        id=question_id,
                        type=q_data["type"],
                        text=q_data["text"],
                        options=q_data.get("options", []),
                        correct_answer=q_data.get("correct_answer"),
                        xp_reward=q_data.get("xp_reward", 10),
                    )
                )

            # Create lesson
            lesson = Lesson(
                id=lesson_id,
                title=lesson_data["title"],
                category=lesson_data.get("category", "general"),
                difficulty=lesson_data.get("difficulty", "beginner"),
                duration_minutes=lesson_data.get("duration_minutes", 5),
                learning_objectives=lesson_data.get("learning_objectives", []),
                prerequisites=lesson_data.get("prerequisites", []),
                sections=sections,
                quiz_questions=quiz_questions,
                xp_reward=lesson_data.get("xp_reward", 50),
                next_lesson=lesson_data.get("next_lesson"),
            )

            # Cache it
            self._lessons_cache[lesson_id] = lesson

            logger.info("Lesson loaded", lesson_id=lesson_id, sections=len(sections))
            return self._lesson_to_dict(lesson)

        except Exception as e:
            logger.error("Failed to load lesson", lesson_id=lesson_id, error=str(e))
            return None

    def _lesson_to_dict(self, lesson: Lesson) -> Dict:
        """Convert Lesson dataclass to dict for API compatibility"""
        return {
            "id": lesson.id,
            "title": lesson.title,
            "category": lesson.category,
            "difficulty": lesson.difficulty,
            "duration_minutes": lesson.duration_minutes,
            "learning_objectives": lesson.learning_objectives,
            "prerequisites": lesson.prerequisites,
            "sections": [
                {
                    "type": s.type,
                    "content": s.content,
                    "fiml_query": s.fiml_query,
                    "metadata": s.metadata
                }
                for s in lesson.sections
            ],
            "quiz": {
                "questions": [
                    {
                        "id": q.id,
                        "type": q.type,
                        "text": q.text,
                        "options": q.options,
                        "correct_answer": q.correct_answer,
                        "xp_reward": q.xp_reward
                    }
                    for q in lesson.quiz_questions
                ]
            },
            "xp_reward": lesson.xp_reward,
            "next_lesson": lesson.next_lesson
        }

    async def render_lesson(
        self, lesson: Union[Lesson, Dict[str, Any]], user_id: str, include_fiml_data: bool = True
    ) -> str:
        """
        Render lesson with live data

        Args:
            lesson: Lesson object or dict to render
            user_id: User identifier
            include_fiml_data: Whether to fetch live FIML data

        Returns:
            Rendered lesson text
        """
        output = []

        # Handle both dict and Lesson object
        if isinstance(lesson, dict):
            lesson_title = lesson.get("title", "Untitled")
            lesson_duration = lesson.get("duration_minutes", 0)
            lesson_difficulty = lesson.get("difficulty", "unknown")
            lesson_objectives = lesson.get("learning_objectives", [])
            lesson_sections = lesson.get("sections", [])
        else:
            lesson_title = lesson.title
            lesson_duration = lesson.duration_minutes
            lesson_difficulty = lesson.difficulty
            lesson_objectives = lesson.learning_objectives
            lesson_sections = lesson.sections

        # Header
        output.append(f"📚 **{lesson_title}**\n")
        # Safely handle difficulty title case
        difficulty_display = str(lesson_difficulty).title() if lesson_difficulty else "Unknown"
        output.append(f"⏱️ {lesson_duration} minutes | " f"📊 {difficulty_display}\n")

        # Learning objectives
        if lesson_objectives:
            output.append("\n**Learning Objectives:**")
            for obj in lesson_objectives:
                output.append(f"• {obj}")
            output.append("")

        # Render sections
        for section in lesson_sections:
            # Handle both dict and LessonSection object
            if isinstance(section, dict):
                section_type = section.get("type")
                section_content = section.get("content", "")
                section_fiml_query = section.get("fiml_query")
            else:
                section_type = section.type
                section_content = section.content
                section_fiml_query = section.fiml_query

            if section_type == "introduction":
                output.append(section_content)
                output.append("")

            elif section_type == "live_example":
                output.append("📊 **Live Example:**")

                if include_fiml_data and section_fiml_query:
                    # Placeholder for FIML data
                    output.append("\n_[Live market data would appear here]_")
                    if isinstance(section_fiml_query, dict):
                        output.append(f"_Query: {section_fiml_query.get('symbol', 'N/A')}_\n")

                output.append(section_content)
                output.append("")

            elif section_type == "explanation":
                output.append(section_content)
                output.append("")

            elif section_type == "chart":
                output.append("📈 **Chart:**")
                output.append("_[Chart would be generated here]_\n")
                output.append(section_content)
                output.append("")

            elif section_type == "key_takeaways":
                output.append("🔑 **Key Takeaways:**")
                # Parse content as bullet points
                for line in section_content.split("\n"):
                    if line.strip():
                        output.append(f"• {line.strip()}")
                output.append("")

        # Footer
        if isinstance(lesson, dict):
            lesson_xp = lesson.get("xp_reward", 0)
            lesson_quiz = lesson.get("quiz", {}).get("questions", [])
        else:
            lesson_xp = lesson.xp_reward
            lesson_quiz = lesson.quiz_questions

        output.append(f"✨ Complete this lesson to earn **{lesson_xp} XP**")

        if lesson_quiz:
            output.append(f"📝 Quiz: {len(lesson_quiz)} questions")

        return "\n".join(output)

    async def check_prerequisites(self, user_id: str, lesson: Lesson) -> tuple[bool, List[str]]:
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
        completed = user_progress.get("completed", set())

        missing = [prereq for prereq in lesson.prerequisites if prereq not in completed]

        return len(missing) == 0, missing

    async def mark_completed(self, user_id: str, lesson_id: str):
        """Mark lesson as completed for user"""
        if user_id not in self._user_progress:
            self._user_progress[user_id] = {"completed": set(), "in_progress": set()}

        self._user_progress[user_id]["completed"].add(lesson_id)
        if lesson_id in self._user_progress[user_id]["in_progress"]:
            self._user_progress[user_id]["in_progress"].remove(lesson_id)

        logger.info("Lesson completed", user_id=user_id, lesson_id=lesson_id)

    async def get_next_lesson(self, user_id: str, current_lesson_id: str) -> Optional[str]:
        """Get next recommended lesson"""
        current = await self.load_lesson(current_lesson_id)
        if current and current.next_lesson:
            return current.next_lesson
        return None

    async def get_user_progress(self, user_id: str) -> Dict:
        """Get user's learning progress"""
        return self._user_progress.get(user_id, {"completed": set(), "in_progress": set()})

    def create_sample_lesson(self, lesson_id: str = "stock_basics_001"):
        """Create a sample lesson for demonstration"""
        sample = {
            "id": lesson_id,
            "title": "Understanding Stock Prices",
            "category": "foundations",
            "difficulty": "beginner",
            "duration_minutes": 5,
            "learning_objectives": [
                "Understand bid-ask spread",
                "Read price charts",
                "Interpret volume data",
            ],
            "prerequisites": [],
            "sections": [
                {
                    "type": "introduction",
                    "content": "Every second, millions of stock trades happen worldwide. "
                    "Let's explore what makes prices move using real market data!",
                },
                {
                    "type": "live_example",
                    "content": "Notice the bid and ask prices above? The bid is what buyers are "
                    "willing to pay, the ask is what sellers want. The difference is the spread.",
                    "fiml_query": {"symbol": "AAPL", "market": "US"},
                },
                {
                    "type": "explanation",
                    "content": "The **spread** is the market's transaction cost. In liquid stocks "
                    "like AAPL, it's tiny (often $0.01). In less liquid stocks, it can be much wider.",
                },
                {
                    "type": "key_takeaways",
                    "content": "Bid-ask spread = transaction cost\n"
                    "Liquid stocks have narrow spreads\n"
                    "Volume indicates market interest",
                },
            ],
            "quiz": {
                "questions": [
                    {
                        "id": "q1",
                        "type": "multiple_choice",
                        "text": "If Bid=$100 and Ask=$100.05, what is the spread?",
                        "options": [
                            {"text": "$0.05", "correct": True},
                            {"text": "$100", "correct": False},
                            {"text": "$200.05", "correct": False},
                        ],
                        "correct_answer": "$0.05",
                        "xp_reward": 10,
                    }
                ]
            },
            "xp_reward": 50,
            "next_lesson": "stock_basics_002",
        }

        # Save to file
        self.lessons_path.mkdir(parents=True, exist_ok=True)
        lesson_file = self.lessons_path / f"{lesson_id}.yaml"

        with open(lesson_file, "w") as f:
            yaml.dump(sample, f, default_flow_style=False)

        logger.info("Sample lesson created", lesson_id=lesson_id)
        return lesson_file

    # Methods expected by tests
    def load_lesson_from_file(self, file_path: str) -> Optional[Dict]:
        """
        Load lesson from YAML file (synchronous version for tests)

        Args:
            file_path: Path to lesson YAML file

        Returns:
            Lesson data dictionary or None
        """
        try:
            with open(file_path, "r") as f:
                lesson_data = yaml.safe_load(f)
            return lesson_data
        except Exception as e:
            logger.error("Failed to load lesson from file", file_path=file_path, error=str(e))
            return None

    def validate_lesson(self, lesson_data: Dict) -> bool:
        """
        Validate lesson structure

        Args:
            lesson_data: Lesson data dictionary

        Returns:
            True if valid
        """
        required_fields = ["id", "title"]
        for field in required_fields:
            if field not in lesson_data:
                logger.error("Missing required field", field=field)
                return False
        return True

    def mark_lesson_started(self, user_id: str, lesson_id: str):
        """
        Mark lesson as started for user

        Args:
            user_id: User identifier
            lesson_id: Lesson identifier
        """
        if user_id not in self._user_progress:
            self._user_progress[user_id] = {}

        if "lessons" not in self._user_progress[user_id]:
            self._user_progress[user_id]["lessons"] = {}

        self._user_progress[user_id]["lessons"][lesson_id] = {
            "status": "in_progress",
            "started_at": datetime.now(UTC).isoformat(),
        }

        logger.info("Lesson started", user_id=user_id, lesson_id=lesson_id)

    def mark_lesson_completed(self, user_id: str, lesson_id: str):
        """
        Mark lesson as completed for user

        Args:
            user_id: User identifier
            lesson_id: Lesson identifier
        """
        if user_id not in self._user_progress:
            self._user_progress[user_id] = {}

        if "lessons" not in self._user_progress[user_id]:
            self._user_progress[user_id]["lessons"] = {}

        self._user_progress[user_id]["lessons"][lesson_id] = {
            "status": "completed",
            "completed_at": datetime.now(UTC).isoformat(),
        }

        logger.info("Lesson completed", user_id=user_id, lesson_id=lesson_id)

    def is_lesson_in_progress(self, user_id: str, lesson_id: str) -> bool:
        """
        Check if lesson is in progress for user

        Args:
            user_id: User identifier
            lesson_id: Lesson identifier

        Returns:
            True if in progress
        """
        if user_id not in self._user_progress:
            return False

        lessons = self._user_progress[user_id].get("lessons", {})
        lesson_data = lessons.get(lesson_id, {})

        return lesson_data.get("status") == "in_progress"

    def is_lesson_completed(self, user_id: str, lesson_id: str) -> bool:
        """
        Check if lesson is completed for user

        Args:
            user_id: User identifier
            lesson_id: Lesson identifier

        Returns:
            True if completed
        """
        if user_id not in self._user_progress:
            return False

        lessons = self._user_progress[user_id].get("lessons", {})
        lesson_data = lessons.get(lesson_id, {})

        return lesson_data.get("status") == "completed"

    def can_access_lesson(self, user_id: str, lesson: Dict) -> bool:
        """
        Check if user can access lesson (prerequisites met)

        Args:
            user_id: User identifier
            lesson: Lesson data dictionary

        Returns:
            True if can access
        """
        prerequisites = lesson.get("prerequisites", [])

        if not prerequisites:
            return True

        # Check if all prerequisites are completed
        for prereq_id in prerequisites:
            if not self.is_lesson_completed(user_id, prereq_id):
                return False

        return True
