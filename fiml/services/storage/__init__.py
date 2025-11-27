"""
Storage abstraction layer for API key management (BYOK)

This module defines the interface for key storage backends,
enabling platform-agnostic key management across:
- File storage (Telegram bot)
- Database storage (Web interface)
- Cloud storage (ChatGPT plugin)
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class KeyStorageInterface(ABC):
    """
    Abstract base class for API key storage backends

    All storage implementations must provide:
    - Encrypted key storage and retrieval
    - User-scoped key management
    - Provider metadata handling
    - Thread-safe operations
    """

    @abstractmethod
    async def store(
        self,
        user_id: str,
        provider: str,
        encrypted_key: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store an encrypted API key for a user

        Args:
            user_id: User identifier (platform-specific)
            provider: Provider identifier (alpha_vantage, polygon, etc.)
            encrypted_key: Already encrypted key string
            metadata: Optional provider metadata (tier, limits, etc.)

        Returns:
            True if stored successfully
        """
        pass

    @abstractmethod
    async def retrieve(self, user_id: str, provider: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve encrypted API key and metadata

        Args:
            user_id: User identifier
            provider: Provider identifier

        Returns:
            Dict with encrypted_key, metadata, added_at or None if not found
        """
        pass

    @abstractmethod
    async def delete(self, user_id: str, provider: str) -> bool:
        """
        Delete a stored API key

        Args:
            user_id: User identifier
            provider: Provider identifier

        Returns:
            True if deleted successfully
        """
        pass

    @abstractmethod
    async def list_all(self, user_id: str) -> List[str]:
        """
        List all providers for which user has stored keys

        Args:
            user_id: User identifier

        Returns:
            List of provider identifiers
        """
        pass

    @abstractmethod
    async def update_metadata(
        self,
        user_id: str,
        provider: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Update metadata for an existing key

        Args:
            user_id: User identifier
            provider: Provider identifier
            metadata: New metadata dict

        Returns:
            True if updated successfully
        """
        pass

    @abstractmethod
    async def get_all_keys(self, user_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all keys and metadata for a user

        Args:
            user_id: User identifier

        Returns:
            Dict mapping provider -> {encrypted_key, metadata, added_at}
        """
        pass
