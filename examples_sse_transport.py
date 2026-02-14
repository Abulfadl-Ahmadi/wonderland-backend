"""
Example: Server-Sent Events (SSE) Transport for LLM Streaming

This demonstrates how the transport-agnostic LLMService enables easy addition
of new transports like SSE without duplicating provider logic.

To use:
1. Add this to apps/llm_chat/api/v1/views/
2. Add to urls:
   path('stream/', StreamChatAPIView.as_view(), name='stream_chat'),
3. Call from client:
   fetch('http://localhost:8000/api/v1/chat/stream/', {
     method: 'POST',
     headers: {'Authorization': 'Bearer <token>'},
     body: JSON.stringify({conversation_id, content, model_slug})
   })
   .then(resp => resp.body.getReader())
"""

import json
import logging
from typing import Generator

from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import StreamingHttpResponse
from rest_framework.permissions import IsAuthenticated

from services import LLMService
from repositories import LLMChatRepository
from selectors_layer import LLMChatSelectors
from apps.llm_chat.models import LLMModel


logger = logging.getLogger(__name__)


def _stream_sse_events(
    user,
    conversation_id: str,
    content: str,
    model_slug: str = None,
) -> Generator[str, None, None]:
    """
    Generator yielding Server-Sent Events for LLM streaming.
    Each line is formatted as: data: {json}\n\n
    """
    try:
        # Validate conversation ownership
        conversation = SelectorLLMChatSelectors.get_user_conversation_detail(
            user, conversation_id
        )
        if not conversation:
            yield f'data: {json.dumps({"type": "error", "error": "Conversation not found"})}\n\n'
            return

        # Store user message
        user_message = LLMChatRepository.create_user_message(
            conversation=conversation,
            content=content,
            user=user,
        )

        # Select model
        if not model_slug:
            pref = LLMChatSelectors.get_user_preferences(user)
            if pref and pref.default_model:
                model_slug = pref.default_model.slug
            else:
                models = LLMChatSelectors.list_active_models()
                if models:
                    model_slug = models[0].slug

        if not model_slug:
            yield f'data: {json.dumps({"type": "error", "error": "No model available"})}\n\n'
            return

        # Get model
        model = LLMModel.objects.filter(
            slug=model_slug,
            is_active=True,
            provider__is_active=True,
        ).first()
        if not model:
            yield f'data: {json.dumps({"type": "error", "error": f"Model {model_slug} not found"})}\n\n'
            return

        # Build context
        messages = LLMChatSelectors.list_messages(conversation)
        messages_context = [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]

        # Stream from LLM service (transport-agnostic)
        full_response = ""
        usage_data = None

        for chunk in LLMService.stream_completion(model_slug, messages_context):
            chunk_type = chunk.get("type")

            if chunk_type == "delta":
                delta = chunk.get("delta", "")
                if delta:
                    full_response += delta
                    # Send delta event
                    yield f'data: {json.dumps({"type": "delta", "delta": delta})}\n\n'

            elif chunk_type == "done":
                usage_data = chunk.get("usage")
                # Send completion event
                yield f'data: {json.dumps({
                    "type": "done",
                    "usage": usage_data,
                })}\n\n'

            elif chunk_type == "error":
                yield f'data: {json.dumps({
                    "type": "error",
                    "error": chunk.get("error_message", "Unknown error"),
                })}\n\n'
                return

        # Store assistant message
        if full_response and usage_data:
            LLMChatRepository.create_assistant_message(
                conversation=conversation,
                content=full_response,
                model_used=model,
                usage=usage_data,
                user=user,
            )

    except Exception as exc:
        logger.exception(f"Error in SSE streaming: {exc}")
        yield f'data: {json.dumps({"type": "error", "error": str(exc)})}\n\n'


@api_view(['POST'])
def stream_chat(request: Request):
    """
    Server-Sent Events endpoint for LLM streaming.
    
    POST /api/v1/chat/stream/
    {
        "conversation_id": "<uuid>",
        "content": "user message",
        "model_slug": "gpt-4" (optional)
    }
    
    Response: text/event-stream
    data: {"type": "delta", "delta": "..."}
    data: {"type": "delta", "delta": "..."}
    data: {"type": "done", "usage": {...}}
    """
    # Require authentication
    if not request.user or not request.user.is_authenticated:
        return StreamingHttpResponse(
            [f'data: {json.dumps({"type": "error", "error": "Unauthorized"})}\n\n'],
            content_type="text/event-stream",
            status=401,
        )

    # Extract payload
    try:
        payload = request.data or {}
        conversation_id = payload.get("conversation_id")
        content = payload.get("content", "").strip()
        model_slug = payload.get("model_slug")

        if not conversation_id or not content:
            return StreamingHttpResponse(
                [f'data: {json.dumps({"type": "error", "error": "Missing conversation_id or content"})}\n\n'],
                content_type="text/event-stream",
                status=400,
            )
    except Exception as exc:
        return StreamingHttpResponse(
            [f'data: {json.dumps({"type": "error", "error": f"Invalid request: {str(exc)}"})}\n\n'],
            content_type="text/event-stream",
            status=400,
        )

    # Stream response
    return StreamingHttpResponse(
        _stream_sse_events(
            user=request.user,
            conversation_id=conversation_id,
            content=content,
            model_slug=model_slug,
        ),
        content_type="text/event-stream",
    )


# ============================================================================
# CLIENT EXAMPLE (JavaScript)
# ============================================================================

# To use from browser:
# 
# const eventSource = new EventSource('/api/v1/chat/stream/', {
#   method: 'POST',
#   headers: {
#     'Authorization': `Bearer ${jwtToken}`,
#     'Content-Type': 'application/json',
#   },
#   body: JSON.stringify({
#     conversation_id: '<uuid>',
#     content: 'Hello, world!',
#     model_slug: 'gpt-4'
#   })
# });
#
# Note: EventSource doesn't support POST, so you'd use fetch:
#
# const resp = await fetch('/api/v1/chat/stream/', {
#   method: 'POST',
#   headers: {
#     'Authorization': `Bearer ${jwtToken}`,
#     'Content-Type': 'application/json',
#   },
#   body: JSON.stringify({...payload})
# });
#
# const reader = resp.body.getReader();
# const decoder = new TextDecoder();
#
# while (true) {
#   const {done, value} = await reader.read();
#   if (done) break;
#   
#   const text = decoder.decode(value);
#   const lines = text.split('\n');
#   for (const line of lines) {
#     if (line.startsWith('data: ')) {
#       const json = JSON.parse(line.slice(6));
#       if (json.type === 'delta') {
#         console.log(json.delta);  // Token
#       } else if (json.type === 'done') {
#         console.log('Finished:', json.usage);
#       }
#     }
#   }
# }
