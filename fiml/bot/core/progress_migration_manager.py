"""
Component: Progress Migration Manager
Handles user progress data migration during updates
"""

from datetime import datetime
from typing import Any, Callable, Dict

import structlog

logger = structlog.get_logger(__name__)


class ProgressMigrationManager:
    """
    Migrates user progress data between schema versions

    Features:
    - Schema version tracking
    - Automatic data migration
    - Backward compatibility
    - Progress preservation
    - XP and achievement migration

    Schema Versions:
    - 1.0: Current production schema
    - Future versions: To be defined as needed
    """

    CURRENT_SCHEMA_VERSION = "1.0"

    def __init__(self):
        """Initialize migration manager"""
        # Register migration functions
        self._migrations: Dict[str, Callable] = {
            "0.9": self._migrate_0_9_to_1_0,
            # Future migrations registered here
            # "1.0": self._migrate_1_0_to_1_1,
        }

        logger.info(
            "ProgressMigrationManager initialized",
            current_version=self.CURRENT_SCHEMA_VERSION,
            migrations=len(self._migrations)
        )

    def migrate_user_data(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate user data to current schema version

        Args:
            user_data: User's progress data (may be old schema)

        Returns:
            Migrated data in current schema
        """
        current_version = user_data.get("schema_version", "0.9")

        if current_version == self.CURRENT_SCHEMA_VERSION:
            # Already current
            return user_data

        logger.info(
            "Migrating user data",
            user_id=user_data.get("user_id", "unknown"),
            from_version=current_version,
            to_version=self.CURRENT_SCHEMA_VERSION
        )

        # Apply migrations in sequence
        migrated_data = user_data.copy()
        migration_count = 0

        while current_version != self.CURRENT_SCHEMA_VERSION:
            if current_version not in self._migrations:
                logger.error(
                    "No migration path available",
                    from_version=current_version,
                    to_version=self.CURRENT_SCHEMA_VERSION
                )
                # Return original data rather than corrupt it
                return user_data

            # Apply migration
            try:
                migrated_data = self._migrations[current_version](migrated_data)
                current_version = migrated_data["schema_version"]
                migration_count += 1

                logger.debug(
                    "Migration step completed",
                    step=migration_count,
                    new_version=current_version
                )
            except Exception as e:
                logger.error(
                    "Migration failed",
                    from_version=current_version,
                    error=str(e)
                )
                # Return original data on migration failure
                return user_data

        logger.info(
            "User data migration completed",
            user_id=migrated_data.get("user_id", "unknown"),
            steps=migration_count
        )

        return migrated_data

    def _migrate_0_9_to_1_0(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate from schema 0.9 to 1.0

        Changes in 1.0:
        - Added lesson version tracking
        - Added schema version field
        - Added migration timestamp
        """
        migrated = data.copy()

        # Add lesson version tracking to in-progress lessons
        if "lessons" in migrated:
            for lesson_id, lesson_data in migrated["lessons"].items():
                if "version" not in lesson_data:
                    # Assume version 1.0 for existing lessons
                    lesson_data["version"] = "1.0"

                # Add started_at if missing
                if "started_at" not in lesson_data:
                    lesson_data["started_at"] = datetime.now().isoformat()

                # Add last_accessed if missing
                if "last_accessed" not in lesson_data:
                    lesson_data["last_accessed"] = datetime.now().isoformat()

        # Add version to completed lessons
        if "lesson_completions" in migrated:
            for lesson_id, completion_data in migrated["lesson_completions"].items():
                if "version" not in completion_data:
                    completion_data["version"] = "1.0"

        # Add schema version
        migrated["schema_version"] = "1.0"

        # Add migration timestamp
        migrated["migrated_at"] = datetime.now().isoformat()

        logger.info(
            "Migrated user data from 0.9 to 1.0",
            user_id=migrated.get("user_id", "unknown"),
            lessons=len(migrated.get("lessons", {})),
            completions=len(migrated.get("lesson_completions", {}))
        )

        return migrated

    def preserve_in_progress_lesson(
        self,
        user_id: str,
        lesson_id: str,
        old_version: str,
        new_version: str
    ) -> Dict[str, Any]:
        """
        Handle in-progress lesson when version changes

        Strategy:
        1. If compatible (minor/patch): Auto-migrate to new version
        2. If incompatible (major): Offer user choice

        Args:
            user_id: User identifier
            lesson_id: Lesson identifier
            old_version: Version user started with
            new_version: New lesson version

        Returns:
            Migration decision data with action and message
        """
        from fiml.bot.core.lesson_version_manager import LessonVersionManager

        version_manager = LessonVersionManager()
        compatibility = version_manager.check_compatibility(
            old_version,
            new_version,
            lesson_id
        )

        if compatibility.action in ["continue", "migrate"]:
            # Auto-migrate compatible changes
            logger.info(
                "Auto-migrating in-progress lesson",
                user_id=user_id,
                lesson_id=lesson_id,
                old_version=old_version,
                new_version=new_version,
                action=compatibility.action
            )

            return {
                "action": "auto_migrate",
                "new_version": new_version,
                "notify_user": compatibility.notify_user,
                "message": compatibility.message
            }

        else:
            # Breaking change - require user choice
            logger.warning(
                "Breaking change detected for in-progress lesson",
                user_id=user_id,
                lesson_id=lesson_id,
                old_version=old_version,
                new_version=new_version
            )

            return {
                "action": "user_choice",
                "options": [
                    {
                        "id": "continue_old",
                        "label": "Continue with original",
                        "description": "Finish with the version you started"
                    },
                    {
                        "id": "restart_new",
                        "label": "Restart with new version",
                        "description": "Start over with improvements (XP preserved)"
                    }
                ],
                "notify_user": True,
                "message": compatibility.message or (
                    f"📚 This lesson has been significantly updated!\n\n"
                    f"You're currently on version {old_version}, "
                    f"but version {new_version} is now available.\n\n"
                    f"Choose how to proceed:"
                )
            }

    def validate_migrated_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate that migrated data has correct structure

        Args:
            data: Migrated user data

        Returns:
            True if valid, False otherwise
        """
        required_fields = ["user_id", "schema_version"]

        for field in required_fields:
            if field not in data:
                logger.error("Missing required field after migration", field=field)
                return False

        # Validate schema version
        if data["schema_version"] != self.CURRENT_SCHEMA_VERSION:
            logger.error(
                "Schema version mismatch after migration",
                expected=self.CURRENT_SCHEMA_VERSION,
                actual=data.get("schema_version")
            )
            return False

        # Validate lesson progress structure
        if "lessons" in data:
            for lesson_id, lesson_data in data["lessons"].items():
                if "version" not in lesson_data:
                    logger.error(
                        "Lesson missing version after migration",
                        lesson_id=lesson_id
                    )
                    return False

        logger.debug("Migrated data validation passed")
        return True

    def create_migration_snapshot(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create snapshot of user data before migration

        Args:
            user_data: Original user data

        Returns:
            Snapshot with timestamp
        """
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "schema_version": user_data.get("schema_version", "unknown"),
            "data": user_data.copy()
        }

        logger.debug(
            "Created migration snapshot",
            user_id=user_data.get("user_id", "unknown")
        )

        return snapshot

    def rollback_migration(
        self,
        current_data: Dict[str, Any],
        snapshot: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Rollback migration using snapshot

        Args:
            current_data: Current (possibly corrupted) data
            snapshot: Pre-migration snapshot

        Returns:
            Restored data
        """
        logger.warning(
            "Rolling back migration",
            user_id=current_data.get("user_id", "unknown"),
            snapshot_version=snapshot.get("schema_version", "unknown")
        )

        # Restore from snapshot
        restored = snapshot["data"].copy()

        # Preserve any XP/achievements earned during failed migration
        if "gamification" in current_data:
            current_xp = current_data["gamification"].get("total_xp", 0)
            snapshot_xp = restored.get("gamification", {}).get("total_xp", 0)

            if current_xp > snapshot_xp:
                # User earned XP during migration, preserve it
                if "gamification" not in restored:
                    restored["gamification"] = {}
                restored["gamification"]["total_xp"] = current_xp

                logger.info(
                    "Preserved XP earned during failed migration",
                    xp_preserved=current_xp - snapshot_xp
                )

        return restored
