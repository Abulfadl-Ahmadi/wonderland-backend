# LLM Service - Quick Reference

## Entry Points

### For Frontend (WebSocket)
```python
# Uses the ChatConsumer implemented in Task 3
# WebSocket URL: ws://localhost:8000/ws/chat/

# Connect with JWT token, send:
{
  "type": "send",
  "payload": {
    "conversation_id": "<uuid>",
    "content": "Your message",
    "model_slug": "gpt-4-turbo",  # optional
    "credential_id": "<uuid>"     # optional
  }
}

# Receive streaming response:
{"type": "assistant.delta", "delta": "token"}
{"type": "assistant.delta", "delta": "..."}
{"type": "assistant.done", "message_id": "...", "usage": {...}}
```

### For SSE Endpoint (Future)
```python
# POST /api/v1/chat/stream/
# with same payload as WebSocket

# Receive SSE stream:
data: {"type": "delta", "delta": "token"}
data: {"type": "delta", "delta": "..."}
data: {"type": "done", "usage": {...}}
```

## LLMService API

### Main Method
```python
from services import LLMService

# Generator yielding chunks
for chunk in LLMService.stream_completion(
    model_slug="gpt-4-turbo",
    messages=[
        {"role": "system", "content": "You are helpful..."},
        {"role": "user", "content": "Hello"},
    ],
    provider="openrouter",        # default
    temperature=0.7,              # optional
    top_p=0.9,                    # optional
    max_tokens=100,               # optional
):
    print(chunk)  # Handle based on chunk["type"]
```

## Chunk Types

### Delta Chunk
```json
{
  "type": "delta",
  "delta": "token text",
  "raw_chunk": {...}
}
```
- Yields for every token
- `delta` may be empty string
- `raw_chunk` is raw provider response

### Done Chunk
```json
{
  "type": "done",
  "delta": "",
  "usage": {
    "prompt_tokens": 42,
    "completion_tokens": 195,
    "total_tokens": 237
  },
  "raw_response": {...}
}
```
- Yields once after all deltas
- Contains usage metadata
- `raw_response` is full provider final response

### Error Chunk
```json
{
  "type": "error",
  "error_code": "rate_limit_exceeded",
  "error_message": "OpenRouter HTTP 429",
  "raw": {...}
}
```
- Yields on any error (network, API, etc.)
- May not include usage if error occurred mid-stream
- No more chunks after error

## Consumer Pattern

### WebSocket Consumer (Implemented)
```python
async for chunk in self._stream_openrouter(...):
    if chunk["type"] == "delta":
        # Send token to client
        await self.send_json({"type": "assistant.delta", "delta": chunk["delta"]})
    
    elif chunk["type"] == "done":
        # Store message and send completion
        assistant_msg = await self._create_assistant_message(
            content=full_text,
            usage=chunk.get("usage"),
            raw_response=chunk.get("raw_response"),
            ...
        )
        await self.send_json({"type": "assistant.done", "message_id": "..."})
    
    elif chunk["type"] == "error":
        # Send error to client
        await self.send_error(chunk["error_message"])
```

### SSE Endpoint (Example)
```python
def stream_sse_events():
    for chunk in LLMService.stream_completion(...):
        if chunk["type"] == "delta":
            yield f'data: {json.dumps({"delta": chunk["delta"]})}\n\n'
        elif chunk["type"] == "done":
            yield f'data: {json.dumps({"type": "done", "usage": chunk["usage"]})}\n\n'
        elif chunk["type"] == "error":
            yield f'data: {json.dumps({"error": chunk["error_message"]})}\n\n'
```

## Files

| File | Purpose |
|------|---------|
| `services/llm_service.py` | Transport-agnostic streaming interface |
| `services/openrouter_service.py` | OpenRouter provider implementation |
| `apps/llm_chat/ws/consumers.py` | WebSocket transport using LLMService |
| `examples_sse_transport.py` | Example SSE transport (future) |

## Error Codes

Common `error_code` values:
- `rate_limit_exceeded` - Too many requests
- `invalid_api_key` - API key not valid
- `model_not_found` - Model doesn't exist
- `network_error` - Connection issue
- `http_error` - HTTP error (check error_message)
- `unsupported_provider` - Provider not implemented

## Usage Example

Complete example of using `LLMService.stream_completion()`:

```python
from services import LLMService

model_slug = "gpt-4-turbo"
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Explain quantum computing in 2 sentences."}
]

full_response = ""
usage = None

try:
    for chunk in LLMService.stream_completion(model_slug, messages):
        if chunk["type"] == "delta":
            token = chunk.get("delta", "")
            print(token, end="", flush=True)  # Stream to stdout
            full_response += token
        
        elif chunk["type"] == "done":
            usage = chunk.get("usage")
            print(f"\n\nTokens: {usage.get('total_tokens')}")
        
        elif chunk["type"] == "error":
            print(f"\nError: {chunk['error_message']}")
            exit(1)

    # Store the message
    from repositories import LLMChatRepository
    LLMChatRepository.create_assistant_message(
        conversation=conversation,
        content=full_response,
        usage=usage,
        raw_response=chunk.get("raw_response"),
        user=user,
    )

except Exception as e:
    print(f"Unexpected error: {e}")
```

## Adding a New Transport

1. Create your endpoint/consumer class
2. Import: `from services import LLMService`
3. Consume: `for chunk in LLMService.stream_completion(...)`
4. Format: Transform chunks to your transport format
5. Persist: Use `LLMChatRepository` to store messages

Example structure:
```python
# 1. Entry point (REST view, consumer, etc.)
class MyTransportView:
    def handle_request(self, user, conversation_id, content, model_slug):
        # 2. Validate
        conversation = validate_ownership(user, conversation_id)
        
        # 3. Store user message
        user_msg = create_user_message(conversation, content)
        
        # 4. Stream and format
        for chunk in LLMService.stream_completion(model_slug, context):
            # 5. Send in your transport format
            self.send_to_client(chunk)
            
            # 6. Collect metadata on done
            if chunk["type"] == "done":
                usage = chunk.get("usage")
                raw = chunk.get("raw_response")
        
        # 7. Persist
        create_assistant_message(conversation, full_text, usage)
```

All transports follow the same pattern!
