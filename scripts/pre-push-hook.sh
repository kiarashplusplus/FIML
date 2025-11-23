#!/bin/bash
# Pre-push hook for FIML
# This hook runs linting and tests before pushing code
# It mimics the CI pipeline to catch issues early

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 Running pre-push checks..."
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: Not in FIML project root${NC}"
    exit 1
fi

# Check if ruff is available
if ! command -v ruff &> /dev/null; then
    echo -e "${YELLOW}⚠️  Warning: ruff is not installed, skipping linting${NC}"
    echo -e "${YELLOW}Install dependencies with: pip install -e \".[dev]\"${NC}"
else
    # 1. Run ruff linting
    echo "📝 Running ruff linter..."
    if ruff check fiml/; then
        echo -e "${GREEN}✅ Linting passed${NC}"
    else
        echo -e "${RED}❌ Linting failed${NC}"
        echo -e "${YELLOW}Tip: Run 'ruff check --fix fiml/' to auto-fix issues${NC}"
        exit 1
    fi
    echo ""
fi

# 2. Run type checking (optional, matches CI behavior)
if command -v mypy &> /dev/null; then
    echo "🔍 Running mypy type checker..."
    if mypy_output=$(mypy fiml/ 2>&1); then
        echo -e "${GREEN}✅ Type checking passed${NC}"
    else
        # Show summary of errors (first and last few lines)
        error_count=$(echo "$mypy_output" | grep -c "error:" || echo "0")
        echo -e "${YELLOW}⚠️  Type checking found $error_count issues (non-blocking)${NC}"
        echo "$mypy_output" | head -5
        if [ "$error_count" -gt "10" ]; then
            echo "..."
            echo "$mypy_output" | tail -3
        fi
    fi
    echo ""
fi

# 3. Run test suite
if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}⚠️  Warning: pytest is not installed, skipping tests${NC}"
    echo -e "${YELLOW}Install dependencies with: pip install -e \".[dev]\"${NC}"
else
    # Check if fiml package is installed
    if ! python -c "import fiml" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Warning: fiml package is not installed, skipping tests${NC}"
        echo -e "${YELLOW}Install with: pip install -e \".[dev]\"${NC}"
    else
        echo "🧪 Running test suite..."
        # Set test environment variables (matching CI)
        export FIML_ENV=test
        export REDIS_HOST=localhost
        export POSTGRES_HOST=localhost
        export POSTGRES_DB=fiml_test
        export POSTGRES_USER=fiml_test
        export POSTGRES_PASSWORD=fiml_test_password
        export AZURE_OPENAI_ENDPOINT=https://mock-azure-openai.openai.azure.com/
        export AZURE_OPENAI_API_KEY=mock-api-key-for-testing
        export AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
        export AZURE_OPENAI_API_VERSION=2024-02-15-preview

        # Run tests with --no-docker flag to skip tests requiring Docker
        # This matches the CI behavior and is faster for pre-push checks
        # Show concise output with short traceback
        if pytest --no-docker -q --tb=short; then
            echo -e "${GREEN}✅ Tests passed${NC}"
        else
            echo -e "${RED}❌ Tests failed${NC}"
            echo -e "${YELLOW}Fix the tests before pushing${NC}"
            echo -e "${YELLOW}Or bypass with: git push --no-verify${NC}"
            exit 1
        fi
        echo ""
    fi
fi

echo -e "${GREEN}✅ Pre-push checks completed!${NC}"
echo "🚀 Proceeding with push..."
