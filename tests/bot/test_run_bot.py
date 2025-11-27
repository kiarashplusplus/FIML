"""
Tests for run_bot entry point
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet


class TestRunBot:
    """Test suite for bot entry point"""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Setup test method"""
        self.fernet_key = Fernet.generate_key().decode()

    def test_main_no_token(self, capsys):
        """Test main() when TELEGRAM_BOT_TOKEN is not set"""
        # Ensure token is not set but FERNET_KEY is valid
        with (
            patch.dict(os.environ, {"FERNET_KEY": self.fernet_key}, clear=True),
            patch("fiml.bot.run_bot.load_dotenv"),
        ):
            # Remove the key if it exists
            os.environ.pop("TELEGRAM_BOT_TOKEN", None)

            from fiml.bot.run_bot import main

            main()

        captured = capsys.readouterr()
        assert "TELEGRAM_BOT_TOKEN environment variable not set" in captured.out

    def test_main_with_token(self, tmp_path):
        """Test main() when TELEGRAM_BOT_TOKEN is set"""
        test_token = "test-token-12345"

        with (
            patch.dict(
                os.environ,
                {
                    "TELEGRAM_BOT_TOKEN": test_token,
                    "KEY_STORAGE_PATH": str(tmp_path / "keys"),
                    "FERNET_KEY": self.fernet_key,
                    "ENCRYPTION_KEY": self.fernet_key,
                },
            ),
            patch("fiml.bot.run_bot.TelegramBotAdapter") as mock_adapter,
            patch("fiml.bot.run_bot.load_dotenv"),
        ):
            # Make the adapter's run() raise KeyboardInterrupt to exit
            # Use AsyncMock for run() since it's awaited
            mock_instance = MagicMock()
            mock_instance.application.initialize = AsyncMock()
            mock_instance.application.start = AsyncMock()
            mock_instance.application.updater.start_polling = AsyncMock(
                side_effect=KeyboardInterrupt()
            )
            mock_instance.application.stop = AsyncMock()
            mock_instance.application.shutdown = AsyncMock()
            mock_instance.application.updater.stop = AsyncMock()
            mock_adapter.return_value = mock_instance

            from fiml.bot.run_bot import main

            main()

        # Verify adapter was initialized with correct token
        mock_adapter.assert_called_once()
        assert mock_adapter.call_args[1]["token"] == test_token

    def test_main_with_encryption_key(self, tmp_path):
        """Test main() when ENCRYPTION_KEY is provided"""
        test_token = "test-token-12345"

        with (
            patch.dict(
                os.environ,
                {
                    "TELEGRAM_BOT_TOKEN": test_token,
                    "ENCRYPTION_KEY": self.fernet_key,
                    "KEY_STORAGE_PATH": str(tmp_path / "keys"),
                    "FERNET_KEY": self.fernet_key,
                },
            ),
            patch("fiml.bot.run_bot.TelegramBotAdapter") as mock_adapter,
            patch("fiml.bot.run_bot.load_dotenv"),
        ):
            mock_instance = MagicMock()
            mock_instance.application.initialize = AsyncMock()
            mock_instance.application.start = AsyncMock()
            mock_instance.application.updater.start_polling = AsyncMock(
                side_effect=KeyboardInterrupt()
            )
            mock_instance.application.stop = AsyncMock()
            mock_instance.application.shutdown = AsyncMock()
            mock_instance.application.updater.stop = AsyncMock()
            mock_adapter.return_value = mock_instance

            from fiml.bot.run_bot import main

            main()

        # Verify key manager was initialized with provided key
        # Note: We can't easily check the key manager instance here without more mocking,
        # but successful execution implies the key was valid
        mock_adapter.assert_called_once()

    def test_storage_path_created(self, tmp_path):
        """Test that storage path is created if it doesn't exist"""
        test_token = "test-token-12345"
        storage_path = tmp_path / "new_keys_dir"

        assert not storage_path.exists()

        with (
            patch.dict(
                os.environ,
                {
                    "TELEGRAM_BOT_TOKEN": test_token,
                    "KEY_STORAGE_PATH": str(storage_path),
                    "FERNET_KEY": self.fernet_key,
                    "ENCRYPTION_KEY": self.fernet_key,
                },
            ),
            patch("fiml.bot.run_bot.TelegramBotAdapter") as mock_adapter,
            patch("fiml.bot.run_bot.load_dotenv"),
        ):
            mock_instance = MagicMock()
            mock_instance.application.initialize = AsyncMock()
            mock_instance.application.start = AsyncMock()
            mock_instance.application.updater.start_polling = AsyncMock(
                side_effect=KeyboardInterrupt()
            )
            mock_instance.application.stop = AsyncMock()
            mock_instance.application.shutdown = AsyncMock()
            mock_instance.application.updater.stop = AsyncMock()
            mock_adapter.return_value = mock_instance

            from fiml.bot.run_bot import main

            main()

        # Storage path should be created
        assert storage_path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
