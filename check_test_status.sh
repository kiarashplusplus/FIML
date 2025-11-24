#!/bin/bash
# FIML Test Status Checker
# Quick script to check test status and show summary

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "           FIML Test Status Checker"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if dependencies are installed
if ! python -c "import pytest" 2>/dev/null; then
    echo "❌ pytest not installed. Installing dependencies..."
    pip install -e ".[dev]" --quiet
    echo "✅ Dependencies installed"
fi

echo "Running test suite..."
echo ""

# Run tests and capture output
OUTPUT=$(pytest tests/ -v -m "not live" --tb=no 2>&1 || true)

# Count results
TOTAL=$(echo "$OUTPUT" | grep -oP '\d+(?= (passed|failed|skipped|deselected))' | head -1 || echo "0")
PASSED=$(echo "$OUTPUT" | grep -oP '\d+(?= passed)' || echo "0")
FAILED=$(echo "$OUTPUT" | grep -oP '\d+(?= failed)' || echo "0")
SKIPPED=$(echo "$OUTPUT" | grep -oP '\d+(?= skipped)' || echo "0")
DESELECTED=$(echo "$OUTPUT" | grep -oP '\d+(?= deselected)' || echo "0")

# Calculate percentage
if [ "$TOTAL" -gt 0 ]; then
    PASS_PCT=$(echo "scale=1; $PASSED * 100 / $TOTAL" | bc)
else
    PASS_PCT="0"
fi

# Display summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "                  TEST SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Total Tests:    $TOTAL"
echo "  ✅ Passed:      $PASSED ($PASS_PCT%)"
echo "  ❌ Failed:      $FAILED"
echo "  ⏭️  Skipped:     $SKIPPED"
echo "  🚫 Deselected:  $DESELECTED"
echo ""

# Determine status
if [ "$FAILED" -eq "0" ]; then
    echo "  Status:        🟢 ALL TESTS PASSING!"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 0
else
    echo "  Status:        🔴 TESTS FAILING"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "📋 Failed Test Breakdown:"
    echo ""
    
    # Show which files have failures
    pytest tests/ -v -m "not live" --tb=no 2>&1 | grep "FAILED" | sed 's/FAILED /  ❌ /' | head -20
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "🔧 To fix these issues:"
    echo "   1. Read QUICKSTART_TEST_FIXES.md"
    echo "   2. Use prompts from AI_FIX_PROMPTS.md"
    echo "   3. Run: pytest tests/bot/ -v"
    echo ""
    echo "📚 Documentation:"
    echo "   - Test summary:  cat QUICKSTART_TEST_FIXES.md"
    echo "   - AI prompts:    cat AI_FIX_PROMPTS.md"
    echo "   - Full report:   cat TEST_STATUS_REPORT.md"
    echo ""
    exit 1
fi
