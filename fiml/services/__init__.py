"""
FIML Services Layer

Platform-agnostic services that support multiple interfaces:
- Telegram bot
- Web application
- ChatGPT plugin
- Future platforms
"""

from fiml.services.storage import KeyStorageInterface
from fiml.services.storage.file_storage import FileKeyStorage
from fiml.services.user_key_onboarding_service import UserKeyOnboardingService

__all__ = [
    "UserKeyOnboardingService",
    "KeyStorageInterface",
    "FileKeyStorage",
]
