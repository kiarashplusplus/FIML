"""
Tests for run_bot entry point
"""

import os
from unittest.mock import MagicMock, patch

import pytest


class TestRunBot:
    """Test suite for bot entry point"""

    def test_main_no_token(self, capsys):
        """Test main() when TELEGRAM_BOT_TOKEN is not set"""
        # Ensure token is not set
        with patch.dict(os.environ, {}, clear=True):
            # Remove the key if it exists
            os.environ.pop("TELEGRAM_BOT_TOKEN", None)

            from fiml.bot.run_bot import main

            main()

            captured = capsys.readouterr()
            assert "Error" in captured.out or "TELEGRAM_BOT_TOKEN" in captured.out

    def test_main_with_token(self, tmp_path):
        """Test main() when TELEGRAM_BOT_TOKEN is set"""
        test_token = "test-token-12345"

        with patch.dict(
            os.environ,
            {
                "TELEGRAM_BOT_TOKEN": test_token,
                "KEY_STORAGE_PATH": str(tmp_path / "keys"),
            },
        ), patch("fiml.bot.run_bot.TelegramBotAdapter") as mock_adapter:
            # Make the adapter's run() raise KeyboardInterrupt to exit
            mock_instance = MagicMock()
            mock_instance.run.side_effect = KeyboardInterrupt()
            mock_adapter.return_value = mock_instance

            from fiml.bot.run_bot import main

            main()

            # Verify adapter was created with correct token
            mock_adapter.assert_called_once()
            call_kwargs = mock_adapter.call_args[1]
            assert call_kwargs["token"] == test_token

    def test_main_with_encryption_key(self, tmp_path):
        """Test main() when ENCRYPTION_KEY is provided"""
        from cryptography.fernet import Fernet

        test_token = "test-token-12345"
        # Generate a valid Fernet key (base64-encoded 32 bytes)
        test_encryption_key = Fernet.generate_key().decode()

        with patch.dict(
            os.environ,
            {
                "TELEGRAM_BOT_TOKEN": test_token,
                "ENCRYPTION_KEY": test_encryption_key,
                "KEY_STORAGE_PATH": str(tmp_path / "keys"),
            },
        ), patch("fiml.bot.run_bot.TelegramBotAdapter") as mock_adapter:
            mock_instance = MagicMock()
            mock_instance.run.side_effect = KeyboardInterrupt()
            mock_adapter.return_value = mock_instance

            from fiml.bot.run_bot import main

            main()

            # Adapter was created
            mock_adapter.assert_called_once()

    def test_storage_path_created(self, tmp_path):
        """Test that storage path is created if it doesn't exist"""
        test_token = "test-token-12345"
        storage_path = tmp_path / "new_keys_dir"

        assert not storage_path.exists()

        with patch.dict(
            os.environ,
            {
                "TELEGRAM_BOT_TOKEN": test_token,
                "KEY_STORAGE_PATH": str(storage_path),
            },
        ), patch("fiml.bot.run_bot.TelegramBotAdapter") as mock_adapter:
            mock_instance = MagicMock()
            mock_instance.run.side_effect = KeyboardInterrupt()
            mock_adapter.return_value = mock_instance

            from fiml.bot.run_bot import main

            main()

            # Storage path should be created
            assert storage_path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
