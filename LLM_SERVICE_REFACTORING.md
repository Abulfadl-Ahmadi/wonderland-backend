# Task 4: LLM Service Refactoring - Transport-Agnostic Streaming

## Objective ✓

Decouple LLM response streaming from WebSocket transport, enabling reuse by other transports (SSE, HTTP polling, etc.) while maintaining clean separation between parsing, streaming, and persistence.

## Problem Statement

**Before:** `OpenRouterService.chat_completion_stream()` yielded chunks mixed with WebSocket concerns.
- Consumer had to check for `"error"` and `"usage"` keys to determine chunk type
- Metadata handling was implicit (final chunk detection)
- Coupling between provider implementation and transport layer
- Hard to extend to new transports

**After:** Clean, transport-agnostic generator contract.
- Explicit chunk types: `"delta"`, `"done"`, `"error"`
- Metadata yielded as final chunk ("done" type)
- Provider logic independent of transport
- Easy to add SSE, HTTP polling, or other transports

## Architecture

### Layer 1: Provider Implementation (OpenRouterService)

**Method:** `stream_chat_completion(model_slug, messages, temperature, top_p, max_tokens)`

Yields normalized chunks:
```python
# Delta chunks (streaming tokens)
{"type": "delta", "delta": "token", "raw_chunk": {...}}

# Done chunk (final, after all deltas)
{"type": "done", "delta": "", "usage": {...}, "raw_response": {...}}

# Error chunk (on failure)
{"type": "error", "error_code": "...", "error_message": "...", "raw": {...}}
```

**Responsibilities:**
- Call OpenRouter API with `stream: True`
- Parse Server-Sent Events (SSE) format
- Extract delta text from each chunk
- Track usage metadata from final chunk
- Handle network/HTTP errors
- Yield normalized chunks
- ❌ NOT responsible for: persistence, formatting, transport

### Layer 2: Transport-Agnostic Service (LLMService)

**Method:** `stream_completion(model_slug, messages, provider="openrouter", ...)`

```python
# Wraps provider-specific implementations
for chunk in LLMService.stream_completion(model_slug, messages):
    # chunk: {"type": "delta"/"done"/"error", ...}
```

**Responsibilities:**
- Provider selection abstraction (currently OpenRouter, extensible)
- Unified interface for all transports
- Future: model registry, fallback providers, rate limiting
- ❌ NOT responsible for: persistence, formatting, specific transports

### Layer 3: Transport Implementations

#### WebSocket Consumer (Current)
**File:** [apps/llm_chat/ws/consumers.py](src/apps/llm_chat/ws/consumers.py)

**Usage:** Consumes `LLMService.stream_completion()` via executor
```python
async for chunk in self._stream_openrouter(...):
    if chunk["type"] == "delta":
        await self.send_json({"type": "assistant.delta", "delta": chunk["delta"]})
    elif chunk["type"] == "done":
        # Store in DB, send completion event
        await self.send_json({"type": "assistant.done", ...})
    elif chunk["type"] == "error":
        # Send error to client
        await self.send_json({"type": "assistant.error", ...})
```

**Responsibilities:**
- Authentication & authorization
- Conversation ownership validation
- User message storage
- Streaming chunk formatting for WebSocket
- Assistant message persistence
- Error formatting for clients

#### Future: SSE Endpoint (Example)
```python
# To add: apps/llm_chat/api/v1/views/stream_view.py
from rest_framework.views import APIView
from services import LLMService

class StreamChatAPIView(APIView):
    def post(self, request):
        def event_generator():
            for chunk in LLMService.stream_completion(model_slug, messages):
                if chunk["type"] == "delta":
                    yield f'data: {json.dumps({"delta": chunk["delta"]})}\n\n'
                elif chunk["type"] == "done":
                    yield f'data: {json.dumps({"type": "done", "usage": chunk["usage"]})}\n\n'
                elif chunk["type"] == "error":
                    yield f'data: {json.dumps({"type": "error", "error": chunk["error_message"]})}\n\n'
        
        return StreamingHttpResponse(
            event_generator(),
            content_type="text/event-stream",
        )
```

## Data Flow

```
┌─────────────┐
│  WebSocket  │ (or SSE, polling, etc.)
│   Client    │
└──────┬──────┘
       │
       │ {type: "send", payload: {conversation_id, content, model_slug}}
       ↓
┌─────────────────────────────────────────┐
│     ChatConsumer                        │
│  (or StreamChatAPIView, etc.)           │
│                                         │
│  1. Authenticate user                   │
│  2. Validate conversation ownership     │
│  3. Store user message                  │
│  4. Consume LLMService.stream_completion│
├─────────────────────────────────────────┤
│        LLMService                       │
│   Transport-agnostic                    │
│                                         │
│  provider="openrouter"                  │
└──────────┬──────────────────────────────┘
           │
           ↓
┌─────────────────────────────────────────┐
│    OpenRouterService                    │
│  Provider-specific implementation       │
│                                         │
│  1. Build OpenRouter request            │
│  2. Call /chat/completions (streaming)  │
│  3. Parse SSE chunks                    │
│  4. Extract delta, usage, errors        │
│  5. Yield normalized chunks             │
└──────────┬──────────────────────────────┘
           │
           ↓
┌─────────────────────────────────────────┐
│    OpenRouter API                       │
│    (external service)                   │
└─────────────────────────────────────────┘
```

## Chunk Format Contract

### Delta Chunk
Token during streaming:
```json
{
  "type": "delta",
  "delta": "Quantum computers",
  "raw_chunk": {
    "id": "...",
    "object": "text_completion.chunk",
    "created": 1234567890,
    "model": "gpt-4-turbo",
    "choices": [{
      "index": 0,
      "delta": {"content": "Quantum computers", "role": null},
      "finish_reason": null
    }]
  }
}
```

### Done Chunk
Final metadata after all deltas:
```json
{
  "type": "done",
  "delta": "",
  "usage": {
    "prompt_tokens": 42,
    "completion_tokens": 195,
    "total_tokens": 237
  },
  "raw_response": {
    "id": "...",
    "object": "text_completion",
    "created": 1234567890,
    "model": "gpt-4-turbo",
    "choices": [{
      "index": 0,
      "message": {"role": "assistant", "content": "full response..."},
      "finish_reason": "stop"
    }],
    "usage": {
      "prompt_tokens": 42,
      "completion_tokens": 195,
      "total_tokens": 237
    }
  }
}
```

### Error Chunk
Network or API error:
```json
{
  "type": "error",
  "error_code": "rate_limit_exceeded",
  "error_message": "OpenRouter HTTP 429",
  "raw": {
    "error": {
      "code": "rate_limit_exceeded",
      "message": "Rate limit exceeded",
      "status": 429
    }
  }
}
```

## Files Changed

### Modified
1. **[services/openrouter_service.py](src/services/openrouter_service.py)**
   - ✓ Replaced `chat_completion_stream()` with new normalized chunk format
   - ✓ Removed `_process_stream_chunk()` helper (inlined)
   - Lines: ~50 (net change ~10, cleaner logic)

2. **[apps/llm_chat/ws/consumers.py](src/apps/llm_chat/ws/consumers.py)**
   - ✓ Updated imports: `from services import LLMService`
   - ✓ Updated `_stream_and_store_response()` to handle new chunk types
   - ✓ Updated `_stream_openrouter()` to use `LLMService.stream_completion()`
   - Lines: +5 in consumer, -5 in streaming (net ~0)

3. **[services/__init__.py](src/services/__init__.py)**
   - ✓ Added export: `from .llm_service import LLMService`

### Created  
1. **[services/llm_service.py](src/services/llm_service.py)** (NEW)
   - ✓ `LLMService.stream_completion()` - main entry point
   - ✓ `_stream_openrouter()` - provider delegation
   - ✓ `get_model_info()` - future model metadata support
   - Lines: ~70 (foundation for extensibility)

## Design Patterns

### 1. Provider Abstraction
```python
# Easy to add new providers in future
if provider == "openrouter":
    yield from LLMService._stream_openrouter(...)
elif provider == "anthropic":
    yield from LLMService._stream_anthropic(...)
```

### 2. Transport Independence
Each transport (WebSocket, SSE, HTTP) handles chunks the same way:
```python
for chunk in LLMService.stream_completion(...):
    if chunk["type"] == "delta":
        # Transport-specific formatting (send_json, response.write, etc.)
    elif chunk["type"] == "done":
        # Persist to DB, send final event
    elif chunk["type"] == "error":
        # Handle error, send to client
```

### 3. Metadata Lifecycle
- **Created:** First chunk received from provider
- **Accumulated:** Each delta chunk processed
- **Finalized:** Done chunk includes usage, raw response
- **Stored:** Transport layer handles persistence

## Testing

### Unit Test Strategy
```python
# Test provider: OpenRouterService.stream_chat_completion()
# - Mock HTTP responses
# - Verify chunk format
# - Test error handling

# Test service: LLMService.stream_completion()
# - Mock OpenRouterService
# - Verify provider routing
# - Test unsupported provider error

# Test consumer: ChatConsumer._stream_and_store_response()
# - Mock LLMService
# - Verify chunk handling
# - Verify DB persistence
# - Verify client messages sent
```

### Manual Testing
```bash
# Start server with streaming enabled
python manage.py runserver

# Open WebSocket client
websocat "ws://localhost:8000/ws/chat/" \
  --header "Authorization: Bearer <jwt>"

# Send message, receive streaming deltas
# Verify chunks: type=delta, then type=done
```

## Extension Points

### Adding a New Provider
1. Create `services/anthropic_service.py`
2. Implement `stream_chat_completion()` yielding same chunk format
3. Add to `LLMService._stream_anthropic()`
4. Update provider routing in `LLMService.stream_completion()`

### Adding a New Transport
1. Create endpoint/consumer class
2. Consume `LLMService.stream_completion()`
3. Iterate chunks, format for your transport (WebSocket JSON, SSE format, etc.)
4. Handle persistence (DB storage, etc.)

### Adding Provider Fallback
```python
# Future: if primary provider fails, try secondary
def stream_completion(..., provider="openrouter", fallback="anthropic"):
    try:
        yield from LLMService._stream_by_provider(provider, ...)
    except OpenRouterError:
        if fallback:
            yield from LLMService._stream_by_provider(fallback, ...)
```

## Benefits of Refactoring

✅ **Separation of Concerns**
- Provider logic separate from transport
- DB persistence independent of streaming
- Each layer testable in isolation

✅ **Reusability**
- Same streaming logic for WebSocket, SSE, polling, etc.
- No duplication of provider integrations

✅ **Extensibility**
- Add new providers without touching transports
- Add new transports without touching providers
- Future features (fallback, rate limiting) in LLMService

✅ **Maintainability**
- Clear chunk format contract
- Easy to debug (type field makes chunks identifiable)
- Logging at right layer (provider vs service vs transport)

✅ **Testability**
- Mock at LLMService level for consumer/transport tests
- Mock at OpenRouterService level for LLMService tests
- E2E tests can use real providers with test models

## Backwards Compatibility

**Breaking Changes:** None (internal refactoring)
- `OpenRouterService.chat_completion()` (non-streaming) unchanged
- New method `stream_chat_completion()` is addition, not replacement
- Consumer changes are internal, no API changes

## Future Enhancements

1. **Model Registry**
   - `LLMService.get_model_info()` - returns context window, pricing, capabilities
   - Used for validation, cost calculation, feature detection

2. **Provider Routing**
   - Route by model: `gpt-4` → OpenRouter, `claude-3` → Anthropic
   - User preferences: default provider per user

3. **Rate Limiting**
   - `LLMService` implements per-user/per-provider quotas
   - Yield rate limit errors before calling provider

4. **Response Caching**
   - Cache common prompts at `LLMService` level
   - Reduce API calls to providers

5. **Analytics**
   - Track cost, latency, errors per provider/model/user
   - Optimize routing based on performance
