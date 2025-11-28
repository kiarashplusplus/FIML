from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from fiml.bot.core.gateway import AbstractResponse
from fiml.server import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_bot_message_endpoint():
    # Mock the gateway response
    mock_response = AbstractResponse(
        text="Hello from bot",
        media=[],
        actions=[],
        metadata={"intent": "test"}
    )

    # Mock the gateway instance
    mock_gateway = MagicMock()
    mock_gateway.handle_message = AsyncMock(return_value=mock_response)

    # Patch get_gateway to return our mock
    with patch("fiml.bot.router.get_gateway", return_value=mock_gateway):
        response = client.post(
            "/api/bot/message",
            json={
                "user_id": "test_user",
                "platform": "mobile",
                "text": "Hello"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "Hello from bot"
        assert data["metadata"]["intent"] == "test"

        # Verify gateway was called with correct args
        mock_gateway.handle_message.assert_called_once_with(
            platform="mobile",
            user_id="test_user",
            text="Hello",
            context=None
        )

@pytest.mark.asyncio
async def test_bot_message_endpoint_error():
    # Mock gateway to raise exception
    mock_gateway = MagicMock()
    mock_gateway.handle_message = AsyncMock(side_effect=Exception("Processing failed"))

    with patch("fiml.bot.router.get_gateway", return_value=mock_gateway):
        response = client.post(
            "/api/bot/message",
            json={
                "user_id": "test_user",
                "text": "Hello"
            }
        )

        assert response.status_code == 500
        assert "Processing failed" in response.json()["detail"]

def test_get_gateway_singleton():
    from fiml.bot.router import get_gateway

    # Reset singleton
    with patch("fiml.bot.router._gateway", None):
        # First call should create instance
        g1 = get_gateway()
        assert g1 is not None

        # Second call should return same instance
        g2 = get_gateway()
        assert g1 is g2
