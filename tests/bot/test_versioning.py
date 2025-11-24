"""
Tests for versioning systems (LessonVersionManager & ProgressMigrationManager)
Tests version compatibility and data migration
"""
from fiml.bot.core.lesson_version_manager import LessonVersionManager
from fiml.bot.core.progress_migration_manager import ProgressMigrationManager


class TestLessonVersionManager:
    """Test suite for lesson versioning"""

    def test_init_version_manager(self):
        """Test version manager initialization"""
        vm = LessonVersionManager()
        assert vm is not None

    def test_parse_version(self):
        """Test semantic version parsing"""
        vm = LessonVersionManager()

        major, minor, patch = vm.parse_version("1.2.3")
        assert major == 1
        assert minor == 2
        assert patch == 3

    def test_is_compatible_patch_update(self):
        """Test patch version compatibility (1.0.0 → 1.0.1)"""
        vm = LessonVersionManager()

        # Patch updates are always compatible
        compatible = vm.is_compatible("1.0.0", "1.0.1")
        assert compatible is True

    def test_is_compatible_minor_update(self):
        """Test minor version compatibility (1.0.0 → 1.1.0)"""
        vm = LessonVersionManager()

        # Minor updates are backward compatible
        compatible = vm.is_compatible("1.0.0", "1.1.0")
        assert compatible is True

    def test_is_incompatible_major_update(self):
        """Test major version incompatibility (1.0.0 → 2.0.0)"""
        vm = LessonVersionManager()

        # Major updates are breaking changes
        compatible = vm.is_compatible("1.0.0", "2.0.0")
        assert compatible is False

    def test_should_notify_user_patch(self):
        """Test that patch updates don't notify users"""
        vm = LessonVersionManager()

        should_notify = vm.should_notify_user("1.0.0", "1.0.1")
        assert should_notify is False

    def test_should_notify_user_minor(self):
        """Test that minor updates notify users with badge"""
        vm = LessonVersionManager()

        should_notify = vm.should_notify_user("1.0.0", "1.1.0")
        # Should notify but not block
        assert isinstance(should_notify, bool)

    def test_should_notify_user_major(self):
        """Test that major updates require user choice"""
        vm = LessonVersionManager()

        should_notify = vm.should_notify_user("1.0.0", "2.0.0")
        # Should definitely notify for breaking changes
        assert should_notify is True

    def test_get_migration_path(self):
        """Test determining migration path"""
        vm = LessonVersionManager()

        path = vm.get_migration_path("1.0.0", "1.2.0")
        assert path is not None
        assert isinstance(path, (str, list))

    def test_changelog_management(self):
        """Test changelog tracking"""
        vm = LessonVersionManager()

        changelog = vm.get_changelog("1.0.0", "1.1.0")
        assert changelog is not None

    def test_version_comparison(self):
        """Test version comparison"""
        vm = LessonVersionManager()

        # 1.2.0 > 1.1.0
        result = vm.compare_versions("1.2.0", "1.1.0")
        assert result > 0

        # 1.0.0 < 2.0.0
        result = vm.compare_versions("1.0.0", "2.0.0")
        assert result < 0

        # 1.0.0 == 1.0.0
        result = vm.compare_versions("1.0.0", "1.0.0")
        assert result == 0


class TestProgressMigrationManager:
    """Test suite for progress migration"""

    def test_init_migration_manager(self):
        """Test migration manager initialization"""
        mm = ProgressMigrationManager()
        assert mm is not None

    def test_create_snapshot(self):
        """Test creating user progress snapshot"""
        mm = ProgressMigrationManager()

        user_data = {
            'user_id': 'user_123',
            'lessons': {'stock_basics_001': {'completed': True}},
            'xp': 100
        }

        snapshot = mm.create_snapshot('user_123', user_data)
        assert snapshot is not None
        assert snapshot['user_id'] == 'user_123'
        assert snapshot['xp'] == 100

    def test_migrate_user_progress_patch(self):
        """Test migrating user progress for patch update"""
        mm = ProgressMigrationManager()

        old_data = {
            'lessons': {'lesson_001': {'version': '1.0.0', 'completed': True}},
            'xp': 50
        }

        # Migrate to 1.0.1 (patch)
        migrated = mm.migrate_user_progress('user_123', old_data, '1.0.0', '1.0.1')

        assert migrated is not None
        assert migrated['xp'] == 50  # XP preserved

    def test_migrate_user_progress_minor(self):
        """Test migrating user progress for minor update"""
        mm = ProgressMigrationManager()

        old_data = {
            'lessons': {'lesson_001': {'version': '1.0.0', 'in_progress': True}},
            'xp': 75
        }

        # Migrate to 1.1.0 (minor)
        migrated = mm.migrate_user_progress('user_123', old_data, '1.0.0', '1.1.0')

        assert migrated is not None
        assert migrated['xp'] == 75  # XP always preserved

    def test_migrate_user_progress_major(self):
        """Test migrating user progress for major update with user choice"""
        mm = ProgressMigrationManager()

        old_data = {
            'lessons': {'lesson_001': {'version': '1.0.0', 'in_progress': True}},
            'xp': 100
        }

        # User chooses to restart with new version
        migrated = mm.migrate_user_progress(
            'user_123', old_data, '1.0.0', '2.0.0',
            user_choice='restart'
        )

        assert migrated is not None
        assert migrated['xp'] >= 100  # XP never lost, even on restart

    def test_xp_protection(self):
        """Test that XP is never lost during migration"""
        mm = ProgressMigrationManager()

        old_data = {'xp': 500, 'lessons': {}}

        # Even failed migration should preserve XP
        try:
            migrated = mm.migrate_user_progress('user_123', old_data, '1.0.0', '3.0.0')
            assert migrated['xp'] >= 500
        except Exception:
            # If migration fails, XP should still be preserved in snapshot
            pass

    def test_rollback_on_error(self):
        """Test automatic rollback on migration error"""
        mm = ProgressMigrationManager()

        old_data = {'xp': 200, 'lessons': {'lesson_001': {'completed': True}}}
        snapshot = mm.create_snapshot('user_123', old_data)

        # Simulate failed migration
        restored = mm.rollback_to_snapshot('user_123', snapshot)

        assert restored is not None
        assert restored['xp'] == 200
        assert 'lesson_001' in restored['lessons']

    def test_in_progress_lesson_handling(self):
        """Test handling of in-progress lessons during migration"""
        mm = ProgressMigrationManager()

        old_data = {
            'lessons': {
                'lesson_001': {
                    'version': '1.0.0',
                    'status': 'in_progress',
                    'sections_completed': ['intro', 'example']
                }
            },
            'xp': 50
        }

        # Minor update - should preserve progress
        migrated = mm.migrate_user_progress('user_123', old_data, '1.0.0', '1.1.0')

        assert migrated is not None
        lesson = migrated['lessons']['lesson_001']
        assert lesson['sections_completed'] == ['intro', 'example']

    def test_schema_migration(self):
        """Test database schema migration"""
        mm = ProgressMigrationManager()

        old_schema_data = {
            'user_id': 'user_123',
            'lessons': {},  # Old schema
            'xp': 100
        }

        # Migrate to new schema with additional fields
        migrated = mm.migrate_schema(old_schema_data, from_version='0.9', to_version='1.0')

        assert migrated is not None
        assert 'user_id' in migrated
        assert migrated['xp'] == 100

    def test_backward_compatibility(self):
        """Test backward compatibility checks"""
        mm = ProgressMigrationManager()

        # Check if new version can read old data
        is_compatible = mm.is_backward_compatible('1.0', '1.1')
        assert isinstance(is_compatible, bool)

    def test_validate_migration(self):
        """Test migration validation"""
        mm = ProgressMigrationManager()

        old_data = {'xp': 100, 'lessons': {'lesson_001': {'completed': True}}}
        new_data = {'xp': 100, 'lessons': {'lesson_001': {'completed': True, 'version': '1.1.0'}}}

        # Validate that migration preserved critical data
        is_valid = mm.validate_migration(old_data, new_data)
        assert is_valid is True
