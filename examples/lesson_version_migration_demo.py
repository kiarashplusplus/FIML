#!/usr/bin/env python3
"""
Example: Lesson Version Migration Demo
Demonstrates how lesson versioning and user migration works
"""

import asyncio
from fiml.bot.core.lesson_version_manager import LessonVersionManager, VersionCompatibility
from fiml.bot.core.progress_migration_manager import ProgressMigrationManager


async def demo_version_compatibility():
    """Demo version compatibility checking"""
    print("=" * 60)
    print("DEMO: Version Compatibility Checking")
    print("=" * 60)
    
    version_manager = LessonVersionManager()
    
    # Test cases
    test_cases = [
        ("1.0", "1.0", "Same version"),
        ("1.0", "1.0.1", "Patch update"),
        ("1.0", "1.1", "Minor update"),
        ("1.0", "2.0", "Major update"),
    ]
    
    for user_ver, current_ver, description in test_cases:
        print(f"\n{description}:")
        print(f"  User: v{user_ver} → Current: v{current_ver}")
        
        compat = version_manager.check_compatibility(
            user_ver, current_ver, "stock_basics_001"
        )
        
        print(f"  Compatible: {compat.compatible}")
        print(f"  Action: {compat.action}")
        print(f"  Notify User: {compat.notify_user}")
        if compat.message:
            print(f"  Message:\n{_indent(compat.message, 4)}")


async def demo_user_migration():
    """Demo user data migration"""
    print("\n" + "=" * 60)
    print("DEMO: User Data Migration")
    print("=" * 60)
    
    migration_manager = ProgressMigrationManager()
    
    # Old schema user data (v0.9)
    old_user_data = {
        "user_id": "telegram_123456",
        # No schema_version (old format)
        "lessons": {
            "stock_basics_001": {
                "status": "in_progress",
                "sections_completed": ["introduction"],
                # No version field (old format)
            }
        },
        "lesson_completions": {
            "market_orders_001": {
                "completed_at": "2024-11-20T10:00:00Z",
                "xp_earned": 50,
                # No version field (old format)
            }
        },
        "gamification": {
            "total_xp": 250,
            "level": 3
        }
    }
    
    print("\nOld User Data (Schema 0.9):")
    print(f"  Schema Version: {old_user_data.get('schema_version', 'not set')}")
    print(f"  In-Progress Lessons: {len(old_user_data['lessons'])}")
    print(f"  Completed Lessons: {len(old_user_data['lesson_completions'])}")
    print(f"  Total XP: {old_user_data['gamification']['total_xp']}")
    
    # Migrate to current schema
    migrated_data = migration_manager.migrate_user_data(old_user_data)
    
    print("\nMigrated User Data (Schema 1.0):")
    print(f"  Schema Version: {migrated_data.get('schema_version')}")
    print(f"  In-Progress Lessons: {len(migrated_data['lessons'])}")
    
    # Check lesson versions were added
    for lesson_id, lesson_data in migrated_data["lessons"].items():
        print(f"    - {lesson_id}: version {lesson_data.get('version')}")
    
    print(f"  Completed Lessons: {len(migrated_data['lesson_completions'])}")
    for lesson_id, completion in migrated_data["lesson_completions"].items():
        print(f"    - {lesson_id}: version {completion.get('version')}")
    
    print(f"  Total XP: {migrated_data['gamification']['total_xp']} (preserved)")
    
    # Validate migration
    is_valid = migration_manager.validate_migrated_data(migrated_data)
    print(f"\n  Migration Valid: {is_valid}")


async def demo_in_progress_lesson_update():
    """Demo handling in-progress lesson when version changes"""
    print("\n" + "=" * 60)
    print("DEMO: In-Progress Lesson Update Handling")
    print("=" * 60)
    
    migration_manager = ProgressMigrationManager()
    
    # Scenario 1: Patch update (auto-migrate)
    print("\nScenario 1: Patch Update (1.0 → 1.0.1)")
    result = migration_manager.preserve_in_progress_lesson(
        user_id="user_123",
        lesson_id="stock_basics_001",
        old_version="1.0",
        new_version="1.0.1"
    )
    print(f"  Action: {result['action']}")
    print(f"  Notify User: {result['notify_user']}")
    if result.get('message'):
        print(f"  Message:\n{_indent(result['message'], 4)}")
    
    # Scenario 2: Minor update (auto-migrate with notification)
    print("\nScenario 2: Minor Update (1.0 → 1.1)")
    result = migration_manager.preserve_in_progress_lesson(
        user_id="user_123",
        lesson_id="stock_basics_001",
        old_version="1.0",
        new_version="1.1"
    )
    print(f"  Action: {result['action']}")
    print(f"  Notify User: {result['notify_user']}")
    if result.get('message'):
        print(f"  Message:\n{_indent(result['message'], 4)}")
    
    # Scenario 3: Major update (user choice)
    print("\nScenario 3: Major Update (1.0 → 2.0)")
    result = migration_manager.preserve_in_progress_lesson(
        user_id="user_123",
        lesson_id="stock_basics_001",
        old_version="1.0",
        new_version="2.0"
    )
    print(f"  Action: {result['action']}")
    print(f"  Notify User: {result['notify_user']}")
    if result.get('options'):
        print(f"  Options:")
        for opt in result['options']:
            print(f"    - {opt['label']}: {opt['description']}")
    if result.get('message'):
        print(f"  Message:\n{_indent(result['message'], 4)}")


async def demo_changelog():
    """Demo changelog generation"""
    print("\n" + "=" * 60)
    print("DEMO: Changelog Generation")
    print("=" * 60)
    
    version_manager = LessonVersionManager()
    
    # Note: This would work with actual lesson files
    print("\nChangelog from v1.0 to v1.2:")
    print("  (Would show list of changes between versions)")
    print("  Example:")
    print("    • Updated AAPL example with more context")
    print("    • Added explanation of market makers")
    print("    • Fixed typo in bid-ask spread section")


def _indent(text: str, spaces: int) -> str:
    """Helper to indent multi-line text"""
    indent = " " * spaces
    return "\n".join(indent + line for line in text.split("\n"))


async def main():
    """Run all demos"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "LESSON VERSION MIGRATION DEMO" + " " * 19 + "║")
    print("╚" + "=" * 58 + "╝")
    
    await demo_version_compatibility()
    await demo_user_migration()
    await demo_in_progress_lesson_update()
    await demo_changelog()
    
    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("\nKey Takeaways:")
    print("  ✅ Patch updates: Auto-migrate silently")
    print("  ✅ Minor updates: Auto-migrate with notification")
    print("  ✅ Major updates: User choice to continue or restart")
    print("  ✅ User data: Always preserved through migrations")
    print("  ✅ XP & progress: Never lost, even on rollback")
    print()


if __name__ == "__main__":
    asyncio.run(main())
