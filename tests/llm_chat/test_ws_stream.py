import asyncio
from uuid import uuid4

import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework_simplejwt.tokens import AccessToken

from config.asgi import application
from apps.llm_chat.models import LLMProvider, LLMModel, Conversation


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
async def test_ws_rejects_unauthenticated():
    communicator = WebsocketCommunicator(application, "/ws/chat/")
    connected, _ = await communicator.connect()
    assert not connected


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
async def test_ws_stream_happy_path(monkeypatch):
    User = get_user_model()
    user = User.objects.create_user(phone_number="09123456789", password="Password123")

    provider = LLMProvider.objects.create(name="OpenRouter", slug="openrouter")
    model = LLMModel.objects.create(provider=provider, name="Test Model", slug="test-model")
    conversation = Conversation.objects.create(user=user, title="Test")

    async def fake_stream_response(*args, **kwargs):
        yield {"type": "delta", "delta": "Hello"}
        yield {"type": "done", "delta": "", "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}, "raw_response": {"id": "resp"}}

    from services import ChatStreamService

    monkeypatch.setattr(ChatStreamService, "stream_response", fake_stream_response)

    token = AccessToken.for_user(user)
    communicator = WebsocketCommunicator(
        application,
        "/ws/chat/",
        headers=[(b"authorization", f"Bearer {str(token)}".encode("utf-8"))],
    )
    connected, _ = await communicator.connect()
    assert connected

    await communicator.send_json_to(
        {
            "type": "send",
            "payload": {
                "conversation_id": str(conversation.id),
                "content": "Hi",
                "model_slug": model.slug,
            },
        }
    )

    delta = await communicator.receive_json_from()
    assert delta["type"] == "assistant.delta"
    assert "message_id" in delta
    assert delta["delta"] == "Hello"

    done = await communicator.receive_json_from()
    assert done["type"] == "assistant.done"
    assert "message_id" in done
    assert done["usage"]["totalTokens"] == 2

    await communicator.disconnect()
