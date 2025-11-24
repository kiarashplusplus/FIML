"""
pytest configuration for bot tests
"""

import pytest
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def temp_storage(tmp_path):
    """Provide temporary storage directory"""
    storage = tmp_path / "storage"
    storage.mkdir()
    return storage
