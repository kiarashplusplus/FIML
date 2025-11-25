"""
Component 9: Gamification Engine
XP, levels, streaks, badges, and achievements
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Dict, List, Optional, TypedDict

import structlog

logger = structlog.get_logger(__name__)


class LevelData(TypedDict):
    """Type definition for level data"""
    level: int
    title: str
    xp_required: int


@dataclass
class Badge:
    """Achievement badge"""

    id: str
    name: str
    description: str
    icon: str
    xp_reward: int = 0


@dataclass
class UserStats:
    """User gamification stats"""

    user_id: str
    total_xp: int = 0
    level: int = 1
    streak_days: int = 0
    last_activity: Optional[datetime] = None
    badges: List[str] = field(default_factory=list)
    daily_quests_completed: int = 0
    lessons_completed: int = 0
    quizzes_completed: int = 0

    def __post_init__(self) -> None:
        if self.last_activity is None:
            self.last_activity = datetime.now(UTC)


class GamificationEngine:
    """
    Manages gamification mechanics

    Features:
    - XP and leveling system
    - Daily streaks with freeze mechanics
    - Badges and achievements
    - Daily quests
    - Leaderboards (optional)
    """

    # XP rewards for actions
    XP_REWARDS = {
        "lesson_completed": 50,
        "quiz_perfect": 25,
        "quiz_passed": 15,
        "simulation_completed": 100,
        "daily_quest": 50,
        "streak_day": 10,
        "first_market_query": 20,
        "ai_mentor_interaction": 5,
        "key_added": 30,
    }

    # Level thresholds
    LEVELS: List[LevelData] = [
        {"level": 1, "title": "Novice", "xp_required": 0},
        {"level": 2, "title": "Learner", "xp_required": 100},
        {"level": 3, "title": "Student", "xp_required": 250},
        {"level": 4, "title": "Apprentice", "xp_required": 500},
        {"level": 5, "title": "Practitioner", "xp_required": 1000},
        {"level": 6, "title": "Trader", "xp_required": 2000},
        {"level": 7, "title": "Analyst", "xp_required": 4000},
        {"level": 8, "title": "Expert", "xp_required": 8000},
        {"level": 9, "title": "Master", "xp_required": 16000},
        {"level": 10, "title": "Legend", "xp_required": 32000},
    ]

    # Available badges
    BADGES = {
        "first_lesson": Badge(
            id="first_lesson",
            name="First Steps",
            description="Complete your first lesson",
            icon="🎓",
            xp_reward=10,
        ),
        "week_streak": Badge(
            id="week_streak",
            name="Week Warrior",
            description="7-day learning streak",
            icon="🔥",
            xp_reward=50,
        ),
        "perfect_quiz": Badge(
            id="perfect_quiz",
            name="Perfect Score",
            description="100% on a quiz",
            icon="💯",
            xp_reward=25,
        ),
        "data_master": Badge(
            id="data_master",
            name="Data Master",
            description="Connect 3 data providers",
            icon="🔑",
            xp_reward=50,
        ),
    }

    def __init__(self) -> None:
        self._user_stats: Dict[str, UserStats] = {}
        logger.info("GamificationEngine initialized")

    async def get_or_create_stats(self, user_id: str) -> UserStats:
        """Get user stats or create new"""
        if user_id not in self._user_stats:
            self._user_stats[user_id] = UserStats(user_id=user_id)
        return self._user_stats[user_id]

    async def award_xp(self, user_id: str, action: str, metadata: Optional[Dict] = None) -> Dict:
        """
        Award XP for an action

        Args:
            user_id: User identifier
            action: Action type
            metadata: Optional metadata (difficulty, etc.)

        Returns:
            Result with XP earned, level changes
        """
        stats = await self.get_or_create_stats(user_id)

        # Base XP
        xp = self.XP_REWARDS.get(action, 0)

        # Multipliers
        if stats.streak_days >= 7:
            xp = int(xp * 1.5)  # 7-day streak bonus

        if metadata and metadata.get("difficulty") == "advanced":
            xp = int(xp * 1.3)  # Advanced content bonus

        # Update totals
        old_level = stats.level
        stats.total_xp += xp
        new_level = self._calculate_level(stats.total_xp)

        # Check level up
        level_up = new_level > old_level

        if level_up:
            stats.level = new_level
            logger.info("Level up!", user_id=user_id, old_level=old_level, new_level=new_level)

        # Update activity
        stats.last_activity = datetime.now(UTC)

        result = {
            "xp_earned": xp,
            "total_xp": stats.total_xp,
            "level": new_level,
            "level_up": level_up,
            "level_title": self.get_level_title(new_level),
        }

        if level_up:
            result["level_up_message"] = (
                f"🎉 Level Up! You're now a **{result['level_title']}** (Level {new_level})!"
            )

        return result

    def _calculate_level(self, total_xp: int) -> int:
        """Calculate level from total XP"""
        for level_data in reversed(self.LEVELS):
            if total_xp >= level_data["xp_required"]:
                return level_data["level"]
        return 1

    def get_level_title(self, level: int) -> str:
        """Get title for level"""
        for level_data in self.LEVELS:
            if level_data["level"] == level:
                return level_data["title"]
        return "Unknown"

    async def update_streak(self, user_id: str) -> Dict:
        """
        Update daily streak

        Returns:
            Streak info with days, broken status
        """
        stats = await self.get_or_create_stats(user_id)
        now = datetime.now(UTC)

        if not stats.last_activity:
            # First activity
            stats.streak_days = 1
            stats.last_activity = now
            return {"streak_days": 1, "streak_broken": False}

        # Check time since last activity
        days_since = (now - stats.last_activity).days

        if days_since == 0:
            # Same day, no change
            return {"streak_days": stats.streak_days, "streak_broken": False}

        elif days_since == 1:
            # Next day, increment streak
            stats.streak_days += 1
            stats.last_activity = now

            # Award streak XP
            await self.award_xp(user_id, "streak_day")

            # Check for week streak badge
            if stats.streak_days == 7 and "week_streak" not in stats.badges:
                await self.award_badge(user_id, "week_streak")

            return {"streak_days": stats.streak_days, "streak_broken": False}

        else:
            # Streak broken
            old_streak = stats.streak_days
            stats.streak_days = 1
            stats.last_activity = now

            logger.info("Streak broken", user_id=user_id, old_streak=old_streak)

            return {"streak_days": 1, "streak_broken": True, "old_streak": old_streak}

    async def award_badge(self, user_id: str, badge_id: str) -> bool:
        """Award badge to user"""
        if badge_id not in self.BADGES:
            return False

        stats = await self.get_or_create_stats(user_id)

        if badge_id in stats.badges:
            return False  # Already has badge

        badge = self.BADGES[badge_id]
        stats.badges.append(badge_id)

        # Award XP
        if badge.xp_reward > 0:
            stats.total_xp += badge.xp_reward

        logger.info("Badge awarded", user_id=user_id, badge_id=badge_id, xp_reward=badge.xp_reward)

        return True

    async def check_badge_triggers(self, user_id: str, action: str) -> None:
        """Check if action triggers any badges"""
        stats = await self.get_or_create_stats(user_id)

        if action == "lesson_completed" and stats.lessons_completed == 1:
            await self.award_badge(user_id, "first_lesson")

        # More trigger logic can be added

    async def get_progress_to_next_level(self, user_id: str) -> Dict:
        """Get progress to next level"""
        stats = await self.get_or_create_stats(user_id)

        current_level = stats.level
        next_level = current_level + 1

        # Find XP thresholds
        current_threshold = next(
            (
                level_info["xp_required"]
                for level_info in self.LEVELS
                if level_info["level"] == current_level
            ),
            0,
        )
        next_threshold = next(
            (
                level_info["xp_required"]
                for level_info in self.LEVELS
                if level_info["level"] == next_level
            ),
            None,
        )

        if next_threshold is None:
            # Max level
            return {"current_level": current_level, "max_level": True, "progress": 100}

        xp_for_level = next_threshold - current_threshold
        xp_earned = stats.total_xp - current_threshold
        progress = (xp_earned / xp_for_level) * 100

        return {
            "current_level": current_level,
            "next_level": next_level,
            "current_xp": stats.total_xp,
            "xp_for_next_level": next_threshold,
            "xp_needed": next_threshold - stats.total_xp,
            "progress": min(progress, 100),
            "max_level": False,
        }

    async def get_user_summary(self, user_id: str) -> Dict:
        """Get complete user gamification summary"""
        stats = await self.get_or_create_stats(user_id)
        progress = await self.get_progress_to_next_level(user_id)

        return {
            "user_id": user_id,
            "xp": stats.total_xp,
            "level": stats.level,
            "level_title": self.get_level_title(stats.level),
            "total_xp": stats.total_xp,
            "streak_days": stats.streak_days,
            "badges": [
                {
                    "id": badge_id,
                    "name": self.BADGES[badge_id].name,
                    "icon": self.BADGES[badge_id].icon,
                }
                for badge_id in stats.badges
                if badge_id in self.BADGES
            ],
            "lessons_completed": stats.lessons_completed,
            "quizzes_completed": stats.quizzes_completed,
            "progress_to_next_level": progress,
        }

    # Synchronous wrapper methods for testing compatibility
    def add_xp(self, user_id: str, amount: int, reason: str) -> None:
        """
        Synchronous wrapper for adding XP
        Note: Uses simplified logic for testing
        """
        if user_id not in self._user_stats:
            self._user_stats[user_id] = UserStats(user_id=user_id)

        stats = self._user_stats[user_id]
        old_level = stats.level
        stats.total_xp += amount
        new_level = self._calculate_level(stats.total_xp)

        if new_level > old_level:
            stats.level = new_level
            logger.info("Level up!", user_id=user_id, old_level=old_level, new_level=new_level)

        stats.last_activity = datetime.now(UTC)

    def get_user_xp(self, user_id: str) -> int:
        """Get user's total XP (sync)"""
        if user_id not in self._user_stats:
            return 0
        return self._user_stats[user_id].total_xp

    def get_user_level(self, user_id: str) -> Dict:
        """Get user's level info (sync)"""
        if user_id not in self._user_stats:
            return {"level": 1, "name": "Novice", "xp": 0}

        stats = self._user_stats[user_id]
        return {
            "level": stats.level,
            "name": self.get_level_title(stats.level),
            "xp": stats.total_xp
        }

    def get_user_badges(self, user_id: str) -> List[Dict]:
        """Get user's badges (sync)"""
        if user_id not in self._user_stats:
            return []

        stats = self._user_stats[user_id]
        return [
            {
                "id": badge_id,
                "name": self.BADGES[badge_id].name if badge_id in self.BADGES else badge_id,
                "description": ""
            }
            for badge_id in stats.badges
        ]

    def award_badge_sync(self, user_id: str, badge_id: str, description: str = "") -> bool:
        """Award badge to user (sync version for non-async contexts)"""
        if user_id not in self._user_stats:
            self._user_stats[user_id] = UserStats(user_id=user_id)

        stats = self._user_stats[user_id]
        if badge_id in stats.badges:
            return False

        stats.badges.append(badge_id)
        logger.info("Badge awarded", user_id=user_id, badge_id=badge_id)
        return True

    def has_badge(self, user_id: str, badge_id: str) -> bool:
        """Check if user has a badge (sync)"""
        if user_id not in self._user_stats:
            return False
        return badge_id in self._user_stats[user_id].badges

    def record_daily_activity(self, user_id: str) -> None:
        """Record daily activity for streak (sync)"""
        if user_id not in self._user_stats:
            self._user_stats[user_id] = UserStats(user_id=user_id)

        stats = self._user_stats[user_id]
        today = datetime.now(UTC).date()

        if stats.last_activity:
            last_date = stats.last_activity.date()
            days_diff = (today - last_date).days

            if days_diff == 0:
                # Same day, ensure streak is at least 1
                if stats.streak_days == 0:
                    stats.streak_days = 1
            elif days_diff == 1:
                # Next day, increment streak
                stats.streak_days += 1
            else:
                # Gap in days, reset streak
                stats.streak_days = 1
        else:
            # First activity
            stats.streak_days = 1

        stats.last_activity = datetime.now(UTC)

    def get_streak(self, user_id: str) -> Dict:
        """Get user's streak info (sync)"""
        if user_id not in self._user_stats:
            return {"current_streak": 0, "longest_streak": 0}

        stats = self._user_stats[user_id]
        return {
            "current_streak": stats.streak_days,
            "longest_streak": stats.streak_days  # Simplified
        }

