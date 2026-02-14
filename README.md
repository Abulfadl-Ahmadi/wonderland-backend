# WonderLand

Django backend skeleton for a LLM chat platform.

## Quick start

1. Create a virtual environment and install dependencies:
   ```bash
   pip install -e .
   ```
2. Copy `.env.example` to `.env` and adjust values.
3. Run migrations:
   ```bash
   python manage.py migrate
   ```
4. Start development server:
   ```bash
   python manage.py runserver
   ```

## Required environment variables

- `SECRET_KEY` (required in non-test environments)
- `OPENROUTER_API_KEYS` (comma-separated)
- `OPENROUTER_BASE_URL` (optional; defaults to `https://openrouter.ai/api/v1`)
- `CREDENTIALS_ENCRYPTION_KEY` (Fernet key for stored provider credentials)
- `REDIS_URL` (required for production Channels; defaults to `redis://localhost:6379/1`)
- `LLM_CHAT_MAX_MESSAGE_LENGTH` (optional; defaults to `4000`)

## WebSocket protocol (frontend contract)

WebSocket path: `/ws/chat/`

Authentication: JWT Bearer token via `Authorization` header or `?token=<jwt>` query string.

### Events from client

- `send`
   ```json
   {
      "type": "send",
      "payload": {
         "conversation_id": "<uuid>",
         "content": "user message",
         "model_slug": "gpt-4.1-mini",
         "credential_id": "<uuid>"
      }
   }
   ```

- `ping` (optional)
   ```json
   {"type": "ping"}
   ```

### Events from server

- `assistant.delta`
   ```json
   {
      "type": "assistant.delta",
      "message_id": "<uuid>",
      "delta": "new text only"
   }
   ```

- `assistant.done`
   ```json
   {
      "type": "assistant.done",
      "message_id": "<uuid>",
      "usage": {
         "promptTokens": 123,
         "completionTokens": 456,
         "totalTokens": 579
      },
      "cost": {
         "inputCost": "0.001230",
         "outputCost": "0.004560",
         "totalCost": "0.005790"
      }
   }
   ```

- `assistant.error`
   ```json
   {
      "type": "assistant.error",
      "message_id": "<uuid>",
      "error": "error message"
   }
   ```

### Contract rules

- `message_id` is always included for assistant events.
- `delta` contains only new text (no previously-sent content).
- `assistant.done` includes final `usage` and `cost`.
- `assistant.error` terminates the current stream.

## Channels production requirement

Production must use Redis for the Channels layer. Set `REDIS_URL` and ensure a Redis
instance is reachable by the backend runtime. In-memory channel layers are only used
in local and test settings.
