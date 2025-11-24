"""
Component: Lesson Version Manager
Manages lesson versioning and compatibility checking
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import structlog
import yaml

logger = structlog.get_logger(__name__)


@dataclass
class LessonVersion:
    """Lesson version metadata"""
    version: str
    date: str
    changes: List[str]


@dataclass
class VersionCompatibility:
    """Version compatibility result"""
    compatible: bool
    action: str  # "continue", "migrate", "user_choice", "force_restart"
    notify_user: bool
    message: Optional[str] = None


class LessonVersionManager:
    """
    Manages lesson versions and migration decisions

    Features:
    - Semantic version parsing and comparison
    - Compatibility checking between versions
    - Migration path determination
    - User notification decisions
    - Changelog management

    Version Format: MAJOR.MINOR.PATCH
    - MAJOR: Breaking changes (quiz format change, complete rewrite)
    - MINOR: New content sections, improved examples
    - PATCH: Typo fixes, small clarifications
    """

    def __init__(self, lessons_path: str = "./fiml/bot/content/lessons"):
        """
        Initialize version manager

        Args:
            lessons_path: Path to lessons directory
        """
        self.lessons_path = Path(lessons_path)
        self._version_cache: Dict[str, List[LessonVersion]] = {}

        logger.info("LessonVersionManager initialized", path=str(self.lessons_path))

    def get_lesson_version(self, lesson_id: str, version: str = "latest") -> Optional[LessonVersion]:
        """
        Get specific version metadata

        Args:
            lesson_id: Lesson identifier
            version: Version string or 'latest'

        Returns:
            LessonVersion or None
        """
        # Load versions if not cached
        if lesson_id not in self._version_cache:
            self._load_lesson_versions(lesson_id)

        versions = self._version_cache.get(lesson_id, [])

        if version == "latest":
            return versions[0] if versions else None

        for v in versions:
            if v.version == version:
                return v
        return None

    def _load_lesson_versions(self, lesson_id: str) -> None:
        """Load version history from lesson file"""
        lesson_file = self.lessons_path / f"{lesson_id}.yaml"
        if not lesson_file.exists():
            logger.warning("Lesson file not found", lesson_id=lesson_id)
            return

        try:
            with open(lesson_file, 'r') as f:
                data = yaml.safe_load(f)

            version = data.get('version', '1.0')
            changelog = data.get('changelog', [])

            versions = []
            for entry in changelog:
                versions.append(LessonVersion(
                    version=entry.get('version', version),
                    date=entry.get('date', ''),
                    changes=entry.get('changes', [])
                ))

            # If no changelog, create entry for current version
            if not versions:
                versions.append(LessonVersion(
                    version=version,
                    date=datetime.now().isoformat()[:10],
                    changes=['Initial version']
                ))

            self._version_cache[lesson_id] = versions
            logger.debug("Loaded versions", lesson_id=lesson_id, count=len(versions))

        except Exception as e:
            logger.error("Failed to load lesson versions", lesson_id=lesson_id, error=str(e))

    def check_compatibility(
        self,
        user_version: str,
        current_version: str,
        lesson_id: str
    ) -> VersionCompatibility:
        """
        Check if user's lesson version is compatible with current version

        Args:
            user_version: Version user started with
            current_version: Current lesson version
            lesson_id: Lesson identifier for context

        Returns:
            VersionCompatibility with action and notification details
        """
        # Same version = always compatible
        if user_version == current_version:
            return VersionCompatibility(
                compatible=True,
                action="continue",
                notify_user=False
            )

        # Parse semantic versions
        user_parts = self._parse_version(user_version)
        current_parts = self._parse_version(current_version)

        # Major version change = breaking change
        if user_parts[0] != current_parts[0]:
            logger.warning(
                "Major version mismatch",
                lesson_id=lesson_id,
                user_version=user_version,
                current_version=current_version
            )
            return VersionCompatibility(
                compatible=False,
                action="user_choice",
                notify_user=True,
                message=(
                    "📚 Lesson Updated!\n\n"
                    "This lesson has major improvements. You can:\n"
                    "1️⃣ Continue with your current version\n"
                    "2️⃣ Restart with the new version\n\n"
                    "Your XP and progress are safe either way! 🎓"
                )
            )

        # Minor version change = new content
        elif user_parts[1] != current_parts[1]:
            logger.info(
                "Minor version update",
                lesson_id=lesson_id,
                user_version=user_version,
                current_version=current_version
            )
            return VersionCompatibility(
                compatible=True,
                action="migrate",
                notify_user=True,
                message=(
                    "📖 Lesson Enhanced!\n\n"
                    "New content added to this lesson. "
                    "You'll continue from where you left off. ✨"
                )
            )

        # Patch version = small fixes (auto-migrate, no notification)
        else:
            logger.debug(
                "Patch version update",
                lesson_id=lesson_id,
                user_version=user_version,
                current_version=current_version
            )
            return VersionCompatibility(
                compatible=True,
                action="migrate",
                notify_user=False
            )

    def _parse_version(self, version: str) -> Tuple[int, int, int]:
        """
        Parse semantic version string

        Args:
            version: Version string (e.g., "1.2.3")

        Returns:
            Tuple of (major, minor, patch)
        """
        try:
            parts = version.split('.')
            major = int(parts[0]) if len(parts) > 0 else 0
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
            return (major, minor, patch)
        except (ValueError, IndexError):
            logger.warning("Invalid version format", version=version)
            return (0, 0, 0)

    def get_migration_path(self, from_version: str, to_version: str) -> List[str]:
        """
        Get list of versions between two versions

        Args:
            from_version: Starting version
            to_version: Target version

        Returns:
            List of version strings in migration order
        """
        # For now, direct migration
        # Future: Could support multi-step migrations for complex changes
        return [to_version]

    def should_notify_user(
        self,
        lesson_id: str,
        user_version: str,
        current_version: str
    ) -> bool:
        """
        Determine if user should be notified of changes

        Args:
            lesson_id: Lesson identifier
            user_version: Version user has
            current_version: Current version

        Returns:
            True if significant changes warrant notification
        """
        if user_version == current_version:
            return False

        user_parts = self._parse_version(user_version)
        current_parts = self._parse_version(current_version)

        # Notify on major or minor version changes
        if user_parts[0] != current_parts[0] or user_parts[1] != current_parts[1]:
            return True

        # Don't notify on patch changes
        return False

    def get_changelog(self, lesson_id: str, from_version: str, to_version: str) -> List[str]:
        """
        Get list of changes between two versions

        Args:
            lesson_id: Lesson identifier
            from_version: Starting version
            to_version: Ending version

        Returns:
            List of change descriptions
        """
        if lesson_id not in self._version_cache:
            self._load_lesson_versions(lesson_id)

        versions = self._version_cache.get(lesson_id, [])

        from_parts = self._parse_version(from_version)
        to_parts = self._parse_version(to_version)

        changes = []
        for version_info in versions:
            v_parts = self._parse_version(version_info.version)

            # Include if version is between from and to
            if from_parts < v_parts <= to_parts:
                changes.extend(version_info.changes)

        return changes

    def format_version_notification(
        self,
        lesson_id: str,
        lesson_title: str,
        from_version: str,
        to_version: str
    ) -> str:
        """
        Format a user-friendly notification about version changes

        Args:
            lesson_id: Lesson identifier
            lesson_title: Human-readable lesson title
            from_version: User's version
            to_version: New version

        Returns:
            Formatted notification message
        """
        changes = self.get_changelog(lesson_id, from_version, to_version)

        message = f"📚 {lesson_title} Updated!\n\n"
        message += f"Version {from_version} → {to_version}\n\n"

        if changes:
            message += "What's new:\n"
            for change in changes[:5]:  # Limit to first 5 changes
                message += f"• {change}\n"

            if len(changes) > 5:
                message += f"\n...and {len(changes) - 5} more improvements!\n"

        return message
