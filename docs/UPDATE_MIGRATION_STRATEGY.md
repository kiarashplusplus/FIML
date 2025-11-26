# Update & Migration Strategy for Production Bot

## Executive Summary

This document outlines the comprehensive strategy for handling updates to lessons, code, and bot functionality after the Telegram bot launches in production. It addresses data continuity, user experience, versioning, and zero-downtime deployments.

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Migration Strategy](#migration-strategy)
3. [Implementation Plan](#implementation-plan)
4. [Versioning System](#versioning-system)
5. [Update Types & Procedures](#update-types-procedures)
6. [Rollback Procedures](#rollback-procedures)
7. [Testing & Validation](#testing-validation)

---

## Problem Statement

### Update Scenarios

1. **Lesson Content Updates**
   - Fix typos or errors in existing lessons
   - Update quiz questions
   - Add new FIML data integrations
   - Improve explanations or examples

2. **Code Updates**
   - Bug fixes in components
   - New features (AI mentors, gamification changes)
   - Security patches
   - Performance improvements
   - FIML integration updates

3. **Schema Changes**
   - New lesson metadata fields
   - Quiz question format changes
   - User progress tracking modifications

### User Impact Concerns

- **In-Progress Lessons**: User is halfway through a lesson
- **Completed Lessons**: User already earned XP and badges
- **Quiz History**: User's quiz attempts and scores
- **XP & Levels**: User progression and achievements
- **API Keys**: User's stored provider keys
- **Learning Paths**: User's progress through curriculum

---

## Migration Strategy

### Core Principles

1. **Zero Downtime**: Updates deployed without service interruption
2. **Backward Compatibility**: Old user data works with new code
3. **Graceful Degradation**: Fallbacks for incompatible changes
4. **Data Preservation**: Never lose user progress or achievements
5. **Transparent Updates**: Users informed of significant changes
6. **Rollback Ready**: Can revert to previous version if issues occur

### Data Model with Versioning

```python
# User Progress Schema (with versioning)
{
    "user_id": "telegram_123456",
    "schema_version": "1.0",
    "lessons": {
        "stock_basics_001": {
            "version": "1.2",  # Lesson version user started
            "status": "in_progress",
            "sections_completed": ["introduction", "live_example"],
            "current_section": "explanation",
            "started_at": "2024-11-24T10:00:00Z",
            "last_accessed": "2024-11-24T10:15:00Z"
        }
    },
    "lesson_completions": {
        "stock_basics_001": {
            "completed_at": "2024-11-24T10:30:00Z",
            "version": "1.2",
            "xp_earned": 50,
            "quiz_score": 4,
            "quiz_total": 5
        }
    },
    "gamification": {
        "total_xp": 500,
        "level": 4,
        "badges": ["first_steps", "week_warrior"],
        "streak_days": 7
    }
}
```

### Lesson Versioning Schema

```yaml
# Lesson file with version metadata
id: stock_basics_001
version: "1.2"  # Semantic versioning
changelog:
  - version: "1.2"
    date: "2024-11-24"
    changes:
      - "Updated AAPL example with more context"
      - "Added explanation of market makers"
  - version: "1.1"
    date: "2024-11-20"
    changes:
      - "Fixed typo in bid-ask spread explanation"
  - version: "1.0"
    date: "2024-11-15"
    changes:
      - "Initial release"

title: "Understanding Stock Prices"
category: fundamentals
# ... rest of lesson content
```

---

## Implementation Plan

### Phase 1: Add Versioning Infrastructure (Week 1)

#### 1.1 Lesson Versioning System

**File**: `fiml/bot/core/lesson_version_manager.py`

```python
"""
Manages lesson versioning and migrations
"""

from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime
import yaml
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class LessonVersion:
    """Lesson version metadata"""
    version: str
    date: str
    changes: List[str]


class LessonVersionManager:
    """
    Manages lesson versions and user migration
    
    Features:
    - Version tracking per lesson
    - Migration path detection
    - Backward compatibility checks
    - Change notifications
    """
    
    def __init__(self):
        self._version_cache: Dict[str, List[LessonVersion]] = {}
    
    def get_lesson_version(self, lesson_id: str, version: str = "latest") -> Optional[LessonVersion]:
        """
        Get specific version metadata
        
        Args:
            lesson_id: Lesson identifier
            version: Version string or 'latest'
            
        Returns:
            LessonVersion or None
        """
        if version == "latest":
            versions = self._version_cache.get(lesson_id, [])
            return versions[0] if versions else None
        
        versions = self._version_cache.get(lesson_id, [])
        for v in versions:
            if v.version == version:
                return v
        return None
    
    def is_compatible(self, user_version: str, current_version: str) -> bool:
        """
        Check if user's lesson version is compatible with current
        
        Args:
            user_version: Version user started with
            current_version: Current lesson version
            
        Returns:
            True if compatible (can continue), False if migration needed
        """
        # Same version = always compatible
        if user_version == current_version:
            return True
        
        # Parse semantic versions
        user_parts = self._parse_version(user_version)
        current_parts = self._parse_version(current_version)
        
        # Major version change = breaking change
        if user_parts[0] != current_parts[0]:
            logger.warning(
                "Major version mismatch",
                user_version=user_version,
                current_version=current_version
            )
            return False
        
        # Minor/patch changes are compatible
        return True
    
    def _parse_version(self, version: str) -> tuple:
        """Parse semantic version string"""
        try:
            parts = version.split('.')
            return (int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
        except:
            return (0, 0, 0)
    
    def get_migration_path(self, from_version: str, to_version: str) -> List[str]:
        """
        Get list of versions between two versions
        
        Args:
            from_version: Starting version
            to_version: Target version
            
        Returns:
            List of version strings in order
        """
        # For now, direct migration
        # In future, could support multi-step migrations
        return [to_version]
    
    def should_notify_user(self, lesson_id: str, user_version: str, current_version: str) -> bool:
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
        
        return False
```

#### 1.2 User Progress Migration Manager

**File**: `fiml/bot/core/progress_migration_manager.py`

```python
"""
Handles user progress migration during updates
"""

from typing import Dict, Any, Optional
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
    """
    
    CURRENT_SCHEMA_VERSION = "1.0"
    
    def __init__(self):
        self._migrations = {
            "0.9": self._migrate_0_9_to_1_0,
            # Future migrations registered here
        }
    
    def migrate_user_data(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate user data to current schema version
        
        Args:
            user_data: User's progress data
            
        Returns:
            Migrated data
        """
        current_version = user_data.get("schema_version", "0.9")
        
        if current_version == self.CURRENT_SCHEMA_VERSION:
            return user_data
        
        logger.info(
            "Migrating user data",
            from_version=current_version,
            to_version=self.CURRENT_SCHEMA_VERSION
        )
        
        # Apply migrations in sequence
        migrated_data = user_data.copy()
        while current_version != self.CURRENT_SCHEMA_VERSION:
            if current_version not in self._migrations:
                logger.error("No migration path", version=current_version)
                break
            
            migrated_data = self._migrations[current_version](migrated_data)
            current_version = migrated_data["schema_version"]
        
        return migrated_data
    
    def _migrate_0_9_to_1_0(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from schema 0.9 to 1.0"""
        migrated = data.copy()
        
        # Add lesson version tracking
        if "lessons" in migrated:
            for lesson_id, lesson_data in migrated["lessons"].items():
                if "version" not in lesson_data:
                    lesson_data["version"] = "1.0"  # Assume version 1.0
        
        # Add schema version
        migrated["schema_version"] = "1.0"
        
        logger.info("Migrated user data from 0.9 to 1.0")
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
        1. If compatible: Continue with new version
        2. If incompatible: Offer choice to restart or continue old version
        
        Args:
            user_id: User identifier
            lesson_id: Lesson identifier
            old_version: Version user started
            new_version: New lesson version
            
        Returns:
            Migration decision data
        """
        from fiml.bot.core.lesson_version_manager import LessonVersionManager
        
        version_manager = LessonVersionManager()
        is_compatible = version_manager.is_compatible(old_version, new_version)
        
        if is_compatible:
            # Auto-migrate to new version
            logger.info(
                "Auto-migrating in-progress lesson",
                user_id=user_id,
                lesson_id=lesson_id,
                old_version=old_version,
                new_version=new_version
            )
            return {
                "action": "auto_migrate",
                "new_version": new_version,
                "notify_user": False
            }
        else:
            # Breaking change - ask user
            logger.warning(
                "Breaking change detected",
                user_id=user_id,
                lesson_id=lesson_id,
                old_version=old_version,
                new_version=new_version
            )
            return {
                "action": "user_choice",
                "options": [
                    "continue_old",  # Finish with old version
                    "restart_new"    # Restart with new version
                ],
                "notify_user": True,
                "message": (
                    f"📚 The lesson '{lesson_id}' has been updated!\n\n"
                    f"You can:\n"
                    f"1️⃣ Continue with the original version you started\n"
                    f"2️⃣ Restart with the new improved version\n\n"
                    f"Your progress and XP will be preserved either way."
                )
            }
```

### Phase 2: Update Lesson Engine (Week 1-2)

**Enhanced LessonContentEngine** with version support:

```python
# Add to existing LessonContentEngine class

async def load_lesson(self, lesson_id: str, version: str = "latest") -> Optional[Lesson]:
    """
    Load lesson with version support
    
    Args:
        lesson_id: Lesson identifier
        version: Specific version or 'latest'
        
    Returns:
        Lesson object or None
    """
    cache_key = f"{lesson_id}:{version}"
    
    # Check cache
    if cache_key in self._lessons_cache:
        return self._lessons_cache[cache_key]
    
    # Load from file
    lesson_file = self.lessons_path / f"{lesson_id}.yaml"
    if not lesson_file.exists():
        logger.error("Lesson not found", lesson_id=lesson_id)
        return None
    
    try:
        with open(lesson_file, 'r') as f:
            data = yaml.safe_load(f)
        
        # Extract version
        lesson_version = data.get('version', '1.0')
        
        # If specific version requested and doesn't match, try to load from archive
        if version != "latest" and version != lesson_version:
            archived_lesson = await self._load_archived_version(lesson_id, version)
            if archived_lesson:
                return archived_lesson
            # Fall through to current version if archive not found
        
        # Parse lesson structure
        lesson = self._parse_lesson_yaml(data)
        
        # Cache it
        self._lessons_cache[cache_key] = lesson
        
        logger.info("Lesson loaded", lesson_id=lesson_id, version=lesson_version)
        return lesson
        
    except Exception as e:
        logger.error("Failed to load lesson", lesson_id=lesson_id, error=str(e))
        return None

async def _load_archived_version(self, lesson_id: str, version: str) -> Optional[Lesson]:
    """Load archived lesson version"""
    archive_path = self.lessons_path / "archive" / version / f"{lesson_id}.yaml"
    if not archive_path.exists():
        return None
    
    try:
        with open(archive_path, 'r') as f:
            data = yaml.safe_load(f)
        return self._parse_lesson_yaml(data)
    except Exception as e:
        logger.error("Failed to load archived lesson", error=str(e))
        return None

async def get_user_lesson(self, user_id: str, lesson_id: str) -> Optional[Lesson]:
    """
    Get lesson for specific user (handles in-progress version)
    
    Args:
        user_id: User identifier
        lesson_id: Lesson identifier
        
    Returns:
        Lesson at appropriate version for user
    """
    # Check user's progress to see which version they started
    progress = self._user_progress.get(user_id, {})
    lesson_progress = progress.get("lessons", {}).get(lesson_id)
    
    if lesson_progress and lesson_progress.get("status") == "in_progress":
        # User has in-progress lesson, load their version
        user_version = lesson_progress.get("version", "1.0")
        lesson = await self.load_lesson(lesson_id, user_version)
        
        if lesson:
            # Check if version changed
            current_lesson = await self.load_lesson(lesson_id, "latest")
            if current_lesson and current_lesson.version != user_version:
                # Handle migration
                migration_result = await self._handle_lesson_migration(
                    user_id, lesson_id, user_version, current_lesson.version
                )
                if migration_result.get("action") == "auto_migrate":
                    return current_lesson
        
        return lesson
    else:
        # New lesson for user, load latest
        return await self.load_lesson(lesson_id, "latest")
```

### Phase 3: Deployment Infrastructure (Week 2)

#### Blue-Green Deployment Setup

```yaml
# deploy/blue-green-config.yaml

deployment:
  strategy: blue-green
  
  environments:
    blue:
      version: current
      traffic: 100%
      instances: 3
      
    green:
      version: new
      traffic: 0%
      instances: 3
  
  rollout:
    phases:
      - traffic_split: 10%   # Canary: 10% users on green
        duration: 1h
        rollback_on_error_rate: 5%
        
      - traffic_split: 50%   # Half traffic
        duration: 2h
        rollback_on_error_rate: 3%
        
      - traffic_split: 100%  # Full cutover
        duration: permanent
  
  healthchecks:
    - endpoint: /health
      interval: 30s
      timeout: 5s
      
    - custom_check: user_progress_integrity
      interval: 5m
      
  rollback:
    automatic: true
    triggers:
      - error_rate_threshold: 5%
      - user_complaints: 10
      - database_migration_failure: true
```

#### Database Migration Strategy

```sql
-- Example migration for lesson progress tracking

-- Migration: Add version tracking to user_lesson_progress
-- Version: 2024-11-24-001
-- Reversible: Yes

-- Forward migration
ALTER TABLE user_lesson_progress 
ADD COLUMN lesson_version VARCHAR(10) DEFAULT '1.0',
ADD COLUMN schema_version VARCHAR(10) DEFAULT '1.0',
ADD COLUMN migrated_at TIMESTAMP DEFAULT NULL;

-- Create index for version queries
CREATE INDEX idx_lesson_version ON user_lesson_progress(lesson_id, lesson_version);

-- Backward migration (rollback)
-- ALTER TABLE user_lesson_progress 
-- DROP COLUMN lesson_version,
-- DROP COLUMN schema_version,
-- DROP COLUMN migrated_at;
```

---

## Versioning System

### Semantic Versioning

**Format**: `MAJOR.MINOR.PATCH`

**Lessons**:
- **MAJOR**: Breaking changes (quiz format change, complete rewrite)
- **MINOR**: New content sections, improved examples
- **PATCH**: Typo fixes, small clarifications

**Code**:
- **MAJOR**: Breaking API changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, security patches

### Version Compatibility Matrix

| User Version | Current Version | Action | User Impact |
|--------------|----------------|---------|-------------|
| 1.0 | 1.0 | None | None |
| 1.0 | 1.1 | Auto-migrate | Seamless, no notice |
| 1.0 | 1.5 | Auto-migrate + notify | Continue, see "Updated" badge |
| 1.0 | 2.0 | User choice | Choose: continue or restart |
| 1.x | 2.x | Force restart | Notify + preserve XP |

---

## Update Types & Procedures

### Type 1: Lesson Content Update (Non-Breaking)

**Examples**: Typo fixes, clarifications, updated examples

**Procedure**:
1. Update lesson YAML file
2. Increment patch version (1.0.0 → 1.0.1)
3. Add changelog entry
4. Deploy via blue-green
5. Users auto-migrate seamlessly

**User Impact**: None (transparent update)

**Code**:
```yaml
# Updated lesson file
version: "1.0.1"
changelog:
  - version: "1.0.1"
    date: "2024-11-24"
    changes:
      - "Fixed typo in explanation section"
```

### Type 2: Lesson Enhancement (Minor Update)

**Examples**: New sections, better examples, additional quiz questions

**Procedure**:
1. Update lesson YAML
2. Increment minor version (1.0.0 → 1.1.0)
3. Archive old version
4. Deploy with notification system
5. Users in-progress continue with old version or get choice
6. New users get new version

**User Impact**: Notification of improvement, optional restart

**Notification**:
```
📚 Lesson Updated!

"Understanding Stock Prices" has been improved with:
• More real-world examples
• Interactive price chart
• Additional quiz questions

Your progress: ✅ Preserved
Complete with current version or restart for new content.
```

### Type 3: Code Update (Bug Fix)

**Examples**: Fix gamification XP calculation, quiz scoring bug

**Procedure**:
1. Fix code
2. Test extensively in staging
3. Deploy via blue-green with 10% canary
4. Monitor error rates
5. Full rollout if healthy
6. Auto-rollback if errors spike

**User Impact**: Improved functionality, no data loss

### Type 4: Code Update (New Feature)

**Examples**: New AI mentor persona, advanced quiz types

**Procedure**:
1. Feature flag implementation
2. Deploy code (feature disabled)
3. Test with beta users
4. Gradual rollout via feature flags
5. Full release

**User Impact**: Optional new features, existing features unchanged

### Type 5: Schema Change (Breaking)

**Examples**: New quiz format, lesson structure change

**Procedure**:
1. Implement migration scripts
2. Test migration with production data copy
3. Deploy migration + code together
4. Run migration during low-traffic window
5. Validate data integrity
6. Monitor closely for 24h

**User Impact**: One-time migration, progress preserved

---

## Rollback Procedures

### Automatic Rollback Triggers

1. **Error Rate > 5%**: Immediate rollback
2. **Database Migration Failure**: Block deploy, rollback code
3. **User Progress Corruption**: Emergency rollback
4. **Critical Bug Reports**: Manual trigger

### Rollback Steps

```bash
# 1. Trigger rollback
./scripts/rollback.sh --to-version v1.2.3

# 2. Verify green environment health
./scripts/health-check.sh green

# 3. Switch traffic back to blue (old version)
./scripts/traffic-switch.sh blue 100%

# 4. If database migrated, rollback migration
./scripts/db-migrate-rollback.sh

# 5. Validate user data integrity
./scripts/validate-user-progress.sh

# 6. Notify team
./scripts/alert.sh "Rollback completed to v1.2.3"
```

### Data Preservation During Rollback

- User progress snapshots taken before migration
- Rollback restores snapshot
- Any XP earned during new version is preserved
- Completed lessons remain completed

---

## Testing & Validation

### Pre-Deployment Testing

**1. Lesson Content Testing**
```bash
# Validate all YAML lessons
python scripts/validate_lessons.py

# Test lesson rendering with all versions
python scripts/test_lesson_versions.py

# Verify quiz answers and scoring
python scripts/test_quiz_integrity.py
```

**2. Migration Testing**
```bash
# Test user data migration with production copy
python scripts/test_migration.py --production-copy

# Verify data integrity after migration
python scripts/validate_migrated_data.py

# Test rollback procedure
python scripts/test_rollback.py
```

**3. Integration Testing**
```bash
# End-to-end user flow with new version
python scripts/e2e_test.py --scenario lesson_update

# Test in-progress lesson handling
python scripts/test_in_progress_migration.py
```

### Monitoring During Rollout

**Metrics to Watch**:
- Error rate (< 1% acceptable)
- Lesson completion rate (should not drop)
- XP calculation correctness
- Database query performance
- User complaint rate

**Alerts**:
- Slack alert if error rate > 2%
- PagerDuty if error rate > 5%
- Email digest of user feedback

---

## Summary of Mitigations

### User Impact Mitigations

| Scenario | Mitigation | User Experience |
|----------|-----------|----------------|
| In-progress lesson updated | Load user's original version | Seamless, no interruption |
| Completed lesson updated | Preserve completion, offer "view updates" | Optional review |
| XP system changes | Retroactive XP adjustment | Automatic, fair |
| Quiz answer changes | Grandfather old answers as correct | No penalty |
| Breaking lesson changes | User choice: continue or restart | User control |
| Code deployment issues | Auto-rollback in < 5min | Minimal downtime |
| Database migration | Blue-green with snapshot | Zero data loss |

### Technical Safeguards

1. **Versioning**: Every lesson and schema versioned
2. **Archival**: Old lesson versions archived
3. **Migration Scripts**: Automated, tested, reversible
4. **Blue-Green Deploy**: Zero downtime
5. **Feature Flags**: Gradual rollouts
6. **Monitoring**: Real-time metrics and alerts
7. **Rollback**: Automated on error threshold
8. **Data Snapshots**: Pre-migration backups

### Communication Plan

**User Notifications**:
- Minor updates: In-app badge "Updated" on lesson
- Major updates: Bot message with changelog
- Breaking changes: Interactive choice prompt
- New features: Announcement message with demo

**Team Alerts**:
- Slack: Deploy status, metrics, warnings
- Email: Daily digest of updates
- PagerDuty: Critical issues only

---

## Conclusion

This update and migration strategy ensures:

✅ **Zero data loss**: User progress always preserved  
✅ **Zero downtime**: Blue-green deployments  
✅ **User control**: Choice for breaking changes  
✅ **Transparent updates**: Users informed appropriately  
✅ **Fast rollback**: Automated on issues  
✅ **Production stability**: Tested migrations, monitoring, alerts  

The system handles lesson updates, code changes, and schema migrations gracefully while maintaining user trust and data integrity.
