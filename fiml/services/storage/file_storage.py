"""
File-based storage backend for API keys (Telegram bot)

Extracts and refines the file storage logic from UserProviderKeyManager.
Maintains backward compatibility with existing JSON file format.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from fiml.services.storage import KeyStorageInterface

logger = structlog.get_logger(__name__)


class FileKeyStorage(KeyStorageInterface):
    """
    File-based key storage using encrypted JSON files

    Storage format: {user_id}.json
    Location: ./data/keys/ (configurable)

    File structure:
    {
        "provider_name": {
            "provider": "provider_name",
            "encrypted_key": "...",
            "added_at": "2025-11-27T15:00:00+00:00",
            "metadata": {...}
        }
    }
    """

    def __init__(self, storage_path: str = "./data/keys"):
        """
        Initialize file storage backend

        Args:
            storage_path: Directory path for storing key files
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        logger.info("FileKeyStorage initialized", storage_path=str(self.storage_path))

    def _get_user_file(self, user_id: str) -> Path:
        """Get path to user's key file"""
        return self.storage_path / f"{user_id}.json"

    def _load_user_data(self, user_id: str) -> Dict[str, Dict[str, Any]]:
        """Load user's key data from file"""
        user_file = self._get_user_file(user_id)

        if not user_file.exists():
            return {}

        try:
            with open(user_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load user data", user_id=user_id, error=str(e))
            return {}

    def _save_user_data(self, user_id: str, data: Dict[str, Dict[str, Any]]) -> bool:
        """Save user's key data to file"""
        user_file = self._get_user_file(user_id)

        try:
            with open(user_file, "w") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logger.error("Failed to save user data", user_id=user_id, error=str(e))
            return False

    async def store(
        self,
        user_id: str,
        provider: str,
        encrypted_key: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Store encrypted API key in JSON file"""
        try:
            # Load existing data
            user_data = self._load_user_data(user_id)

            # Add/update provider key
            user_data[provider] = {
                "provider": provider,
                "encrypted_key": encrypted_key,
                "added_at": datetime.now(UTC).isoformat(),
                "metadata": metadata or {}
            }

            # Save
            success = self._save_user_data(user_id, user_data)

            if success:
                logger.info("Key stored", user_id=user_id, provider=provider)

            return success

        except Exception as e:
            logger.error("Failed to store key", user_id=user_id, provider=provider, error=str(e))
            return False

    async def retrieve(self, user_id: str, provider: str) -> Optional[Dict[str, Any]]:
        """Retrieve encrypted key and metadata"""
        user_data = self._load_user_data(user_id)
        return user_data.get(provider)

    async def delete(self, user_id: str, provider: str) -> bool:
        """Delete a provider's key"""
        try:
            user_data = self._load_user_data(user_id)

            if provider not in user_data:
                return False

            # Remove provider
            del user_data[provider]

            # Save updated data
            success = self._save_user_data(user_id, user_data)

            if success:
                logger.info("Key deleted", user_id=user_id, provider=provider)

            return success

        except Exception as e:
            logger.error("Failed to delete key", user_id=user_id, provider=provider, error=str(e))
            return False

    async def list_all(self, user_id: str) -> List[str]:
        """List all providers for user"""
        user_data = self._load_user_data(user_id)
        return list(user_data.keys())

    async def update_metadata(
        self,
        user_id: str,
        provider: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """Update metadata for existing key"""
        try:
            user_data = self._load_user_data(user_id)

            if provider not in user_data:
                return False

            # Update metadata
            user_data[provider]["metadata"] = metadata

            # Save
            return self._save_user_data(user_id, user_data)

        except Exception as e:
            logger.error("Failed to update metadata", user_id=user_id, provider=provider, error=str(e))
            return False

    async def get_all_keys(self, user_id: str) -> Dict[str, Dict[str, Any]]:
        """Get all keys and metadata for user"""
        return self._load_user_data(user_id)
