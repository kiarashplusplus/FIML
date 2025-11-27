#!/usr/bin/env python
"""
Standalone test runner for bot components (bypasses global conftest)
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Run tests directly
if __name__ == "__main__":
    import pytest

    # Run bot tests only
    bot_tests_dir = Path(__file__).parent
    exit_code = pytest.main(
        [
            str(bot_tests_dir),
            "-v",
            "--tb=short",
            "-p",
            "no:cacheprovider",
            "--override-ini=addopts=",  # Clear global addopts
        ]
    )

    sys.exit(exit_code)
