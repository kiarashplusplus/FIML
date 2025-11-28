from unittest.mock import AsyncMock, MagicMock

import pytest

from fiml.bot.education.ai_mentor import AIMentorService, MentorPersona


@pytest.fixture
def mock_azure_client():
    client = MagicMock()  # Remove spec to ensure new methods are accessible
    client.generate_chat_response = AsyncMock(return_value="This is a generated response from AI.")
    return client


@pytest.fixture
def ai_mentor_service(mock_azure_client):
    narrative_generator = MagicMock()  # Remove spec to allow dynamic attributes
    narrative_generator.azure_client = mock_azure_client
    narrative_generator.generate_narrative = AsyncMock()  # Should not be called for general chat

    service = AIMentorService(narrative_generator=narrative_generator)
    return service


@pytest.mark.asyncio
async def test_general_chat_response(ai_mentor_service, mock_azure_client):
    # Test a general question that doesn't trigger symbol extraction
    question = "How are you?"
    user_id = "user123"

    response = await ai_mentor_service.respond(user_id, question, persona=MentorPersona.MAYA)

    # Verify generate_chat_response was called
    mock_azure_client.generate_chat_response.assert_called_once()

    assert response["text"] == "This is a generated response from AI."
    assert response["mentor"] == "Maya"
    call_args = mock_azure_client.generate_chat_response.call_args
    assert "messages" in call_args.kwargs
    messages = call_args.kwargs["messages"]
    assert len(messages) == 2
    assert messages[1]["content"] == question
    assert "Maya" in messages[0]["content"]  # System prompt should contain persona name


@pytest.mark.asyncio
async def test_general_chat_fallback(ai_mentor_service, mock_azure_client):
    # Simulate error
    mock_azure_client.generate_chat_response.side_effect = Exception("API Error")

    question = "Random question"
    user_id = "user123"

    response = await ai_mentor_service.respond(user_id, question, persona=MentorPersona.MAYA)

    # Should fall back to template response
    assert "Maya here!" in response["text"]
