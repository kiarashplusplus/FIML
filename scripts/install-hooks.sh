#!/bin/bash
# Install Git pre-push hook for FIML
# This script copies the pre-push hook to .git/hooks/

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Installing FIML pre-push hook..."

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: Not in FIML project root${NC}"
    exit 1
fi

# Check if .git directory exists
if [ ! -d ".git" ]; then
    echo -e "${RED}Error: .git directory not found${NC}"
    exit 1
fi

# Check if hooks directory exists
if [ ! -d ".git/hooks" ]; then
    echo -e "${YELLOW}Creating .git/hooks directory${NC}"
    mkdir -p .git/hooks
fi

# Check if pre-push hook already exists
if [ -f ".git/hooks/pre-push" ]; then
    echo -e "${YELLOW}Pre-push hook already exists${NC}"
    read -p "Do you want to overwrite it? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled"
        exit 0
    fi
    # Backup existing hook
    cp .git/hooks/pre-push .git/hooks/pre-push.backup
    echo -e "${GREEN}Existing hook backed up to .git/hooks/pre-push.backup${NC}"
fi

# Copy the hook
cp scripts/pre-push-hook.sh .git/hooks/pre-push
chmod +x .git/hooks/pre-push

echo -e "${GREEN}✅ Pre-push hook installed successfully!${NC}"
echo ""
echo "The hook will now run before every git push and check:"
echo "  📝 Linting (ruff)"
echo "  🔍 Type checking (mypy)"
echo "  🧪 Tests (pytest)"
echo ""
echo "To bypass the hook (not recommended), use: git push --no-verify"
