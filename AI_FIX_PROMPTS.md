# AI Fix Prompts - FIML Test Failures

Quick reference guide with ready-to-use AI prompts to fix the 41 failing tests in the FIML repository.

## 🎯 How to Use These Prompts

1. Copy the prompt text
2. Paste into your AI assistant (GitHub Copilot, ChatGPT, Claude, etc.)
3. Review the generated fix
4. Apply the changes
5. Run tests to verify: `pytest tests/bot/<test_file>.py -v`

---

## Gateway Issues (12 failures)

### Prompt 1: Implement Missing Gateway Methods

```
I'm working on the FIML project and the tests in tests/bot/test_gateway.py are failing 
because the UnifiedBotGateway class is missing several required methods and attributes.

Please implement the following in fiml/bot/core/gateway.py:

1. Add a classify() method to UnifiedBotGateway that:
   - Is an async method
   - Accepts parameters: message (AbstractMessage), session (UserSession)
   - Returns an intent object with a 'type' attribute of IntentType enum
   - Classifies messages into: COMMAND, LESSON_REQUEST, AI_QUESTION, MARKET_QUERY, NAVIGATION
   - Detects commands starting with "/"
   - Detects lesson requests with keywords like "learn", "teach", "lesson"
   - Detects market queries with keywords like "price", "stock", "crypto"
   - Defaults to AI_QUESTION for conversational queries

2. Add a metadata attribute to the UserSession class:
   - Should be a dictionary
   - Can store arbitrary session data
   - Should be initialized as empty dict in __init__

3. Add a get_session() method to SessionManager:
   - Is an async method
   - Accepts session_id parameter
   - Returns the session if it exists, None otherwise

Please show the complete implementation.
```

### Prompt 2: Fix Gateway Session State

```
The test_update_session_state and test_multiple_session_isolation tests are failing 
because the UserSession class doesn't have a metadata attribute.

In fiml/bot/core/gateway.py:

1. Add a metadata: dict attribute to UserSession class
2. Initialize it as an empty dict in __init__
3. Ensure it can store arbitrary key-value pairs
4. Make sure each session has its own independent metadata dict

Show me the updated UserSession class definition.
```

---

## Gamification Issues (1 failure)

### Prompt 3: Fix Leaderboard Stats

```
The test_leaderboard_stats test in tests/bot/test_gamification.py is failing because 
the return value is missing the 'xp' field.

In fiml/bot/education/gamification.py, update the get_leaderboard_stats() method to 
include all required fields:

Current issue: AssertionError: assert 'xp' in {'badges': [], 'lessons_completed': 0, ...}

The method should return a dictionary with:
- xp: total XP points (integer)
- level: current level number (integer)
- level_title: level name like "Novice", "Learner", etc. (string)
- badges: list of earned badges (list)
- lessons_completed: count of completed lessons (integer)

Please show the corrected method.
```

---

## Integration Issues (5 failures)

### Prompt 4: Fix Missing DateTime Import

```
Multiple test files are failing with: NameError: name 'datetime' is not defined

Please add the missing datetime import to these files:
- tests/bot/test_integration.py
- tests/bot/test_lesson_quiz.py

Add at the top of each file:
from datetime import datetime, timedelta

Also check if any source files in fiml/bot/ are missing this import.
```

### Prompt 5: Fix Lesson Flow Return Value

```
The test_complete_lesson_flow test in tests/bot/test_integration.py is failing with:
assert None is not None

This means the lesson completion flow is not returning a result.

Please review the lesson flow implementation in fiml/bot/education/lessons.py and ensure:
1. The complete_lesson() method returns a proper result object (not None)
2. The result should include lesson completion status
3. The result should be returned to the caller

Show the corrected method.
```

### Prompt 6: Fix Compliance Filter Response

```
The test_compliance_filtering_in_flow test expects a compliance filter response 
with an 'is_allowed' attribute, but it's failing with:
AttributeError: 'tuple' object has no attribute 'is_allowed'

In the compliance filtering code (likely in fiml/bot/ or fiml/compliance/), ensure:
1. The compliance check returns an object (not a tuple)
2. The object has an 'is_allowed' boolean attribute
3. Update any code that's returning a tuple to return a proper response object

Show the corrected implementation.
```

### Prompt 7: Add get_user_level Method

```
Tests are failing with: AttributeError: 'GamificationEngine' object has no attribute 'get_user_level'

Please add a get_user_level() method to the GamificationEngine class in 
fiml/bot/education/gamification.py:

The method should:
- Be async
- Accept user_id as parameter
- Return the user's current level as an integer
- Get the level from the user's stats

Show the implementation.
```

---

## Key Manager Issues (1 failure)

### Prompt 8: Fix Path Operations

```
The test_key_encryption test is failing with:
TypeError: unsupported operand type(s) for /: 'str' and 'str'

This is a path handling issue in fiml/bot/providers/key_manager.py.

Please fix all path operations in the UserProviderKeyManager class:

1. Import pathlib.Path at the top
2. Convert all path strings to Path objects
3. Use Path operations instead of string division
4. Example fix:
   - WRONG: str_path / str_filename
   - RIGHT: Path(str_path) / str_filename

Show the corrected path handling code in the key encryption method.
```

---

## Lesson/Quiz Issues (7 failures)

### Prompt 9: Add Missing QuizSystem Methods

```
The QuizSystem class in fiml/bot/education/quiz.py is missing methods required by tests.

Please add these async methods to the QuizSystem class:

1. get_session(session_id: str) -> Optional[QuizSession]:
   - Retrieve an existing quiz session by ID
   - Return None if not found

2. answer_question(session_id: str, question_id: str, answer: str) -> dict:
   - Record a user's answer to a question
   - Update the session with the answer
   - Return result with: correct (bool), score (int)

Show the complete implementation of both methods.
```

### Prompt 10: Fix Lesson Content Return Type

```
The test_render_lesson test is failing with:
AttributeError: 'dict' object has no attribute 'title'

The LessonContentEngine.render_lesson() method in fiml/bot/education/lessons.py is 
returning a dict instead of an object.

Please:
1. Create a LessonContent class with attributes: title, content, metadata
2. Update render_lesson() to return a LessonContent object instead of a dict
3. Ensure backward compatibility if needed

Show the LessonContent class and updated render_lesson() method.
```

---

## Provider Configurator Issues (9 failures)

### Prompt 11: Fix Async/Await in Provider Configurator

```
All tests in tests/bot/test_provider_configurator.py are failing with async/await issues:
- TypeError: 'coroutine' object is not subscriptable
- TypeError: argument of type 'coroutine' is not iterable

The FIMLProviderConfigurator class in fiml/bot/providers/configurator.py has async 
methods that are not being properly awaited.

Please fix:

1. Review all methods that return coroutines
2. Ensure async methods use 'async def'
3. Ensure all async method calls use 'await'
4. Fix any code trying to subscript/iterate coroutines before awaiting them

Common patterns to fix:
- WRONG: config = async_method()['key']
- RIGHT: config = await async_method(); value = config['key']

- WRONG: if key in async_method():
- RIGHT: result = await async_method(); if key in result:

Show the corrected async method definitions and call sites.
```

### Prompt 12: Add Missing Configurator Methods

```
The FIMLProviderConfigurator class is missing these methods required by tests:

1. get_fallback_suggestions() - async method
   - Returns a list of alternative providers when primary fails
   - Should suggest providers based on availability and user tier

2. check_provider_health() - async method
   - Checks if a provider is currently operational
   - Returns health status dict with: available (bool), latency (float)

Please implement both methods in fiml/bot/providers/configurator.py.
```

---

## Versioning Issues (5 failures)

### Prompt 13: Fix ProgressMigrationManager API

```
The ProgressMigrationManager class in fiml/bot/education/versioning.py has API mismatches.

Please fix:

1. create_snapshot(data: dict) expects 'user_id' key:
   - Add validation to ensure 'user_id' is in data
   - Raise ValueError if missing

2. migrate_user_progress() is receiving unexpected 'user_choice' parameter:
   - Add user_choice parameter to method signature
   - Use it to determine migration strategy

3. Add missing rollback_to_snapshot() method:
   - Should be async
   - Accept snapshot_id parameter
   - Restore user progress from snapshot

4. Fix migrate_schema() parameters:
   - Change parameters to: from_version, to_version
   - Update implementation to use these parameter names

Show the corrected class with all fixes.
```

### Prompt 14: Fix Snapshot Validation

```
The test_validate_migration test is failing with: assert False is True

This suggests the migration validation logic is incorrect.

In fiml/bot/education/versioning.py, update the validate_migration() method to:
1. Properly validate migration compatibility
2. Return True when migration is valid
3. Return False when migration would cause data loss or incompatibility
4. Check version compatibility rules

Show the corrected validation logic.
```

---

## Deprecation Warnings (50+ warnings)

### Prompt 15: Fix datetime.utcnow() Deprecation

```
There are 50+ deprecation warnings for datetime.utcnow() which is deprecated in Python 3.12+.

Please replace ALL instances of datetime.utcnow() in these files:

1. fiml/sessions/models.py (lines 136, 140)
2. fiml/sessions/store.py (lines 95, 135, 371)

Replace with:
from datetime import datetime, UTC
datetime.now(UTC)

Show the corrected code for each file.
```

### Prompt 16: Fix Redis close() Deprecation

```
There are deprecation warnings for redis.close() which is deprecated since redis-py 5.0.1.

In fiml/sessions/store.py (line 95), replace:
await self._redis.close()

With:
await self._redis.aclose()

Show the corrected code section.
```

---

## Testing Best Practices Prompts

### Prompt 17: Run Specific Test Category

```
Show me how to:
1. Run only the gateway tests
2. Run only failing tests
3. Run tests with verbose output
4. Run tests with coverage report
5. Skip slow/live tests

Provide pytest commands for each scenario.
```

### Prompt 18: Debug Test Failure

```
I have a failing test in tests/bot/test_[filename].py

Help me debug it by:
1. Showing how to run just that one test with maximum verbosity
2. Showing how to drop into debugger on failure (pytest --pdb)
3. Showing how to see the full traceback
4. Suggesting common causes for [specific error type]

Provide the debugging workflow.
```

---

## Batch Fix Prompts

### Prompt 19: Fix All Bot Gateway Issues (Comprehensive)

```
I need to fix all the failing tests in tests/bot/test_gateway.py. Here's what's needed:

FILE: fiml/bot/core/gateway.py

1. UnifiedBotGateway class needs:
   - classify(message: AbstractMessage, session: UserSession) -> Intent
     * Returns intent with type: IntentType enum
     * Classifies: COMMAND (starts with /), LESSON_REQUEST (learn/teach keywords),
       MARKET_QUERY (price/stock keywords), NAVIGATION (menu/back keywords), 
       AI_QUESTION (default)
   
2. UserSession class needs:
   - metadata: dict = field(default_factory=dict)
   - Store arbitrary session data

3. SessionManager class needs:
   - async get_session(session_id: str) -> Optional[UserSession]
   - Return existing session or None

Please provide the complete updated code for all three classes.
```

### Prompt 20: Fix All Bot Quiz System Issues (Comprehensive)

```
I need to fix all failing tests in tests/bot/test_lesson_quiz.py.

FILE: fiml/bot/education/quiz.py

1. Create LessonContent dataclass:
   - title: str
   - content: str
   - metadata: dict

2. Update LessonContentEngine.render_lesson() to return LessonContent object

3. Add QuizSystem methods:
   - async get_session(session_id: str) -> Optional[QuizSession]
   - async answer_question(session_id: str, question_id: str, answer: str) -> dict

4. Ensure datetime is imported: from datetime import datetime, timedelta

Please provide the complete updated code.
```

---

## Verification Prompts

### Prompt 21: Verify Fix Success

```
After applying the fixes, help me verify they worked:

1. Show pytest command to run just the tests I fixed
2. Show how to check if coverage improved
3. Show how to verify no new warnings were introduced
4. Suggest a git commit message for the fixes

Provide a verification checklist.
```

### Prompt 22: Generate Test Report

```
After all fixes are applied, help me generate an updated test report:

1. Run full test suite with coverage
2. Count passing/failing tests
3. List any remaining issues
4. Compare with baseline (620 passing, 41 failing)
5. Generate summary for stakeholders

Show the commands and report template.
```

---

## Summary Checklist

Use this to track which prompts you've used and which issues are fixed:

### Gateway Issues
- [ ] Prompt 1: Implement missing gateway methods
- [ ] Prompt 2: Fix gateway session state

### Gamification Issues  
- [ ] Prompt 3: Fix leaderboard stats

### Integration Issues
- [ ] Prompt 4: Fix missing datetime import
- [ ] Prompt 5: Fix lesson flow return value
- [ ] Prompt 6: Fix compliance filter response
- [ ] Prompt 7: Add get_user_level method

### Key Manager Issues
- [ ] Prompt 8: Fix path operations

### Lesson/Quiz Issues
- [ ] Prompt 9: Add missing quiz system methods
- [ ] Prompt 10: Fix lesson content return type

### Provider Configurator Issues
- [ ] Prompt 11: Fix async/await issues
- [ ] Prompt 12: Add missing configurator methods

### Versioning Issues
- [ ] Prompt 13: Fix progress migration manager API
- [ ] Prompt 14: Fix snapshot validation

### Deprecation Warnings
- [ ] Prompt 15: Fix datetime.utcnow() deprecation
- [ ] Prompt 16: Fix Redis close() deprecation

---

## Quick Reference: Most Common Issues

### Issue Type → Prompt Number
- Missing method → Prompts 1, 7, 9, 12
- Wrong return type → Prompts 3, 5, 6, 10
- Async/await → Prompt 11
- Import missing → Prompt 4
- Path handling → Prompt 8
- API mismatch → Prompts 13, 14
- Deprecation → Prompts 15, 16

---

**Created:** November 24, 2024  
**For Repository:** kiarashplusplus/FIML  
**Purpose:** Quick AI-assisted test fixing
