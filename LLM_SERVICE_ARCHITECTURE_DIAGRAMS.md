# LLM Service Architecture Visualization

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         MULTIPLE TRANSPORTS                             │
│                                                                         │
│  ┌─────────────────┐  ┌──────────────┐  ┌─────────────────────────┐   │
│  │  WebSocket      │  │  SSE         │  │  HTTP Polling           │   │
│  │  Client         │  │  Client      │  │  Client                 │   │
│  └────────┬────────┘  └────┬─────────┘  └────────┬────────────────┘   │
│           │                 │                     │                     │
│           ↓                 ↓                     ↓                     │
│  ┌─────────────────┐  ┌─────────────────────────────────┐             │
│  │  ChatConsumer   │  │  StreamChatAPIView (example)    │  ... more   │
│  │  (Task 3)       │  │  (examples_sse_transport.py)    │             │
│  └────────┬────────┘  └────────┬────────────────────────┘             │
│           │                    │                     │                 │
│           └────────────────────┼─────────────────────┘                │
│                                ↓                                       │
│          ┌─────────────────────────────────────────┐                  │
└──────────│     LLMService                          │──────────────────┘
           │  (Transport-Agnostic)                  │
           │  stream_completion(...)                │
           └────────────┬────────────────────────────┘
                        │
                        │ normalized chunks
                        │ {"type": "delta"|"done"|"error", ...}
                        ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                         PROVIDERS                                       │
│                                                                         │
│  ┌──────────────────────┐        ┌─────────────────────────┐           │
│  │  OpenRouterService   │        │  AnthropicService       │           │
│  │  (IMPLEMENTED)       │        │  (FUTURE)               │           │
│  │                      │        │                         │           │
│  │ stream_chat_         │        │ stream_chat_            │           │
│  │ completion(...)      │        │ completion(...)         │           │
│  │                      │        │                         │           │
│  └──────────┬───────────┘        └────────┬────────────────┘           │
│             │                             │                            │
│             └─────────────┬───────────────┘                            │
│                           ↓                                            │
│          ┌────────────────────────────────┐                           │
│          │   External LLM APIs            │                           │
│          │   ├─ OpenRouter                │                           │
│          │   ├─ Anthropic (future)        │                           │
│          │   └─ Other (future)            │                           │
│          └────────────────────────────────┘                           │
└─────────────────────────────────────────────────────────────────────────┘
```

## Request-Response Flow

```
CLIENT                          TRANSPORT                    SERVICE
  │                              │                            │
  │ {"type": "send",             │                            │
  │  "payload": {...}}           │                            │
  ├────────────────────────────→ │                            │
  │                              │ LLMService.stream_         │
  │                              │ completion(...)            │
  │                              ├───────────────────────────→│
  │                              │                            │ Generator starts
  │                              │                            │
  │                              │ chunk: {                   │
  │                              │   "type": "delta",         │
  │ {"type":                     │   "delta": "..."           │
  │  "assistant.delta",          │ }                          │
  │  "delta": "..."}             │←───────────────────────────┤
  │←───────────────────────────── │                            │
  │                              │                            │
  │ (repeated for each token)    │ (multiple delta chunks)    │
  │                              │                            │
  │ {"type":                     │ chunk: {                   │
  │  "assistant.done",           │   "type": "done",          │
  │  "message_id": "...",        │   "usage": {...},          │
  │  "usage": {...}}             │   "raw_response": {...}    │
  │←───────────────────────────── │ }                          │
  │                              │←───────────────────────────┤
  │                              │                            │
  │ (stream closed)              │ (generator finished)       │
```

## Data Flow: Complete Message Lifecycle

```
1. CLIENT CONNECTS
   ↓
   WebSocket ← → AuthMiddlewareStack
   ↓
   User Authenticated

2. CLIENT SENDS MESSAGE
   ↓
   {
     "type": "send",
     "payload": {
       "conversation_id": "<uuid>",
       "content": "Your message",
       "model_slug": "gpt-4" // optional
     }
   }

3. CONSUMER VALIDATES
   ├─ Validate UUID format
   ├─ Check conversation ownership
   ├─ Validate content non-empty
   └─ Validate model if specified

4. STORE USER MESSAGE
   ↓
   LLMChatRepository.create_user_message()
   └─ INSERT INTO message (role='user', ...)

5. RESOLVE MODEL
   ├─ Use specified model_slug if provided
   ├─ Fall back to user preference
   └─ Fall back to first active model

6. BUILD CONTEXT
   ↓
   LLMChatSelectors.list_messages()
   └─ SELECT * FROM message WHERE conversation_id=...
   └─ Format as [{role, content}, ...]

7. START STREAMING
   ↓
   LLMService.stream_completion()
     ↓
     OpenRouterService.stream_chat_completion()
       ↓
       urllib.request to OpenRouter API
       ↓
       SSE stream from /chat/completions
       ↓
       Parse SSE chunks
       ↓
       Yield normalized chunks for each token
       └─ {"type": "delta", "delta": "..."}

8. RECEIVE DELTAS
   ├─ Consumer accumulates text
   ├─ Format for transport
   └─ Send to client: {"type": "assistant.delta", "delta": "..."}
   ↓
   REPEAT for each token

9. RECEIVE DONE
   ├─ Provider yields: {"type": "done", "usage": {...}}
   ├─ Consumer extract usage
   ├─ Compute costs
   └─ Store assistant message
      ↓
      LLMChatRepository.create_assistant_message()
      └─ INSERT INTO message (role='assistant', content=..., usage=..., ...)

10. SEND COMPLETION
    ↓
    {"type": "assistant.done", "message_id": "...", "usage": {...}}

11. ON ERROR
    ├─ Provider yields: {"type": "error", "error_code": "..."}
    ├─ Consumer handles error
    └─ Send to client: {"type": "assistant.error", "error": "..."}
```

## Layer Responsibilities

```
┌──────────────────────────────────────────────────────────────┐
│  TRANSPORT LAYER (WebSocket, SSE, Polling, etc.)           │
│                                                              │
│  Responsibilities:                                           │
│  • Authenticate user                                         │
│  • Validate request payload                                  │
│  • Check conversation ownership                              │
│  • Store user message                                        │
│  • Consume LLMService.stream_completion()                    │
│  • Format chunks for specific transport                      │
│  • Send to client in transport-specific format               │
│  • Handle errors gracefully                                  │
│  • Store assistant message with metadata                     │
│                                                              │
│  Example: ChatConsumer (WebSocket)                           │
│  Example: StreamChatAPIView (SSE)                            │
└──────────────────────────────────────────────────────────────┘
                            ↓ depends on
┌──────────────────────────────────────────────────────────────┐
│  SERVICE LAYER (LLMService)                                  │
│                                                              │
│  Responsibilities:                                           │
│  • Route to appropriate provider                             │
│  • Provide unified interface for all transports              │
│  • Future: Provider fallback                                 │
│  • Future: Rate limiting                                     │
│  • Future: Response caching                                  │
│  • Future: Model registry                                    │
│                                                              │
│  Current: OpenRouterService                                  │
│  Future: AnthropicService, etc.                              │
└──────────────────────────────────────────────────────────────┘
                            ↓ uses
┌──────────────────────────────────────────────────────────────┐
│  PROVIDER LAYER (OpenRouterService, etc.)                    │
│                                                              │
│  Responsibilities:                                           │
│  • Call external LLM API with stream=true                    │
│  • Parse Server-Sent Events (SSE) format                     │
│  • Extract delta text from each chunk                        │
│  • Track usage metadata                                      │
│  • Handle network errors                                     │
│  • Normalize to standard chunk format                        │
│                                                              │
│  Output: Generator yielding normalized chunks                │
│  {"type": "delta"|"done"|"error", ...}                       │
└──────────────────────────────────────────────────────────────┘
```

## Chunk Flow Diagram

```
PROVIDER (OpenRouterService)
    ↓ Parse SSE
    ├─ {"choices": [{"delta": {"content": "Hello"}}]}
    │  → yield {"type": "delta", "delta": "Hello", ...}
    │
    ├─ {"choices": [{"delta": {"content": " world"}}]}
    │  → yield {"type": "delta", "delta": " world", ...}
    │
    ├─ {"choices": [...], "usage": {"total_tokens": 42}}
    │  → yield {"type": "done", "usage": {...}, ...}
    │
    └─ (stream ends)
    
                ↓ (consumed by)

SERVICE (LLMService)
    ├─ Receives delta chunks
    ├─ Passes through (no modification)
    └─ No buffering, no accumulation
    
                ↓ (consumed by)

TRANSPORT (ChatConsumer)
    ├─ Accumulates full_response from deltas
    ├─ Formats for client: {"type": "assistant.delta", "delta": "..."}
    ├─ On done: Stores in DB
    └─ Sends completion: {"type": "assistant.done", "message_id": "..."}
    
                ↓

CLIENT (WebSocket)
    ├─ Displays each delta token as received
    ├─ Shows final message when done
    └─ Handles errors gracefully
```

## Adding New Transport: Step-by-Step

```
1. Create Transport Class
   └─ MyTransportConsumer / MyTransportView

2. Implement Transport-Specific Entry Point
   ├─ @websocket_connect / @api_view / etc.
   └─ Authenticate user

3. Consume LLMService
   for chunk in LLMService.stream_completion(model_slug, messages):

4. Handle Each Chunk Type
   if chunk["type"] == "delta":
       format_and_send_to_client(chunk)
   elif chunk["type"] == "done":
       persist_to_database(chunk)
   elif chunk["type"] == "error":
       handle_error(chunk)

5. Only Code You Write: Transport-Specific Formatting
   └─ Rest is shared with all transports!
```

## Performance Characteristics

```
┌─────────────────────────────────────────────────────┐
│  STREAMING PERFORMANCE                              │
│                                                     │
│  Time to First Token:                               │
│  Client → Transport → LLMService → Provider → API   │
│  ~200-500ms (mostly network latency)                │
│                                                     │
│  Per-Token Latency:                                 │
│  Negligible (direct streaming, no buffering)        │
│                                                     │
│  Memory Usage:                                      │
│  O(1) - only streaming chunks, not full response    │
│                                                     │
│  Scalability:                                       │
│  Linear with concurrent connections                 │
│  Each connection has own generator instance         │
│                                                     │
│  No queuing, no batching overhead                   │
└─────────────────────────────────────────────────────┘
```

## Error Handling: Insertion Points

```
CLIENT ERROR
    ↓ Invalid auth
    Transport: Close connection with 4001
    
REQUEST ERROR
    ↓ Invalid UUID, missing content
    Transport: Send {"type": "assistant.error", ...}
    
VALIDATION ERROR
    ↓ Conversation not owned, model not found
    Transport: Send {"type": "assistant.error", ...}
    
STREAMING ERROR
    ↓ From LLMService generator
    ↓ e.g., provider error, network error
    Provider: Yield {"type": "error", "error_code": "..."}
    Transport: Catch and send to client
    
DATABASE ERROR
    ↓ On message persistence
    Transport: Catch and send error event
```

This architecture enables clean, scalable, and maintainable LLM streaming across multiple transports!
