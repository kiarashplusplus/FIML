#!/bin/bash
# Pre-push hook for FIML
# This hook runs linting and tests before pushing code
# It mimics the CI pipeline to catch issues early

set -e  # Exit on any error

echo "🔍 Running pre-push checks..."
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: Not in FIML project root${NC}"
    exit 1
fi

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

# 2. Run type checking (optional, matches CI behavior)
echo "🔍 Running mypy type checker..."
if mypy fiml/ 2>/dev/null; then
    echo -e "${GREEN}✅ Type checking passed${NC}"
else
    echo -e "${YELLOW}⚠️  Type checking found issues (non-blocking)${NC}"
fi
echo ""

# 3. Run test suite
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
if pytest -v --no-docker -x; then
    echo -e "${GREEN}✅ Tests passed${NC}"
else
    echo -e "${RED}❌ Tests failed${NC}"
    echo -e "${YELLOW}Fix the tests before pushing${NC}"
    exit 1
fi
echo ""

echo -e "${GREEN}✅ All pre-push checks passed!${NC}"
echo "🚀 Proceeding with push..."
