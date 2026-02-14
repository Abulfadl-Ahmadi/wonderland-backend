/**
 * WebSocket Chat Client Example
 * 
 * Shows how to connect to ChatConsumer and handle streaming responses
 * Install: npm install -g ws  (for Node.js testing)
 */

// ============================================================================
// BROWSER CLIENT EXAMPLE
// ============================================================================

class LLMChatClient {
  constructor(baseUrl = 'ws://localhost:8000', jwtToken = null) {
    this.baseUrl = baseUrl;
    this.jwtToken = jwtToken;
    this.socket = null;
    this.listeners = {
      delta: [],
      done: [],
      error: [],
      connected: [],
      disconnected: []
    };
  }

  /**
   * Connect to WebSocket
   * Note: JWT token should be passed via websocket subprotocol or session cookie
   */
  connect() {
    return new Promise((resolve, reject) => {
      try {
        const wsUrl = `${this.baseUrl}/ws/chat/`;
        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = () => {
          console.log('✓ Connected to chat WebSocket');
          this.emit('connected');
          resolve();
        };

        this.socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.handleServerMessage(data);
          } catch (err) {
            console.error('Failed to parse message:', err);
          }
        };

        this.socket.onerror = (error) => {
          console.error('✗ WebSocket error:', error);
          this.emit('error', { message: 'Connection error' });
          reject(error);
        };

        this.socket.onclose = (event) => {
          console.log(`✗ Disconnected (code: ${event.code})`);
          if (event.code === 4001) {
            console.error('  Reason: Unauthorized (authentication failed)');
          }
          this.emit('disconnected', { code: event.code });
        };
      } catch (err) {
        reject(err);
      }
    });
  }

  /**
   * Send message to LLM
   */
  sendMessage(payload) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }

    const message = {
      type: 'send',
      payload: {
        conversation_id: payload.conversationId,
        content: payload.content,
        ...(payload.modelSlug && { model_slug: payload.modelSlug }),
        ...(payload.credentialId && { credential_id: payload.credentialId })
      }
    };

    console.log('→ Sending message:', message);
    this.socket.send(JSON.stringify(message));
  }

  /**
   * Handle messages from server
   */
  handleServerMessage(data) {
    const { type, ...rest } = data;

    switch (type) {
      case 'assistant.delta':
        console.log('↓ Token:', rest.delta);
        this.emit('delta', rest.delta);
        break;

      case 'assistant.done':
        console.log('✓ Response complete');
        console.log('  Usage:', rest.usage);
        console.log('  Cost:', rest.cost);
        this.emit('done', rest);
        break;

      case 'assistant.error':
        console.error('✗ Error:', rest.error);
        this.emit('error', { message: rest.error });
        break;

      default:
        console.warn('Unknown message type:', type);
    }
  }

  /**
   * Register event listener
   */
  on(event, callback) {
    if (event in this.listeners) {
      this.listeners[event].push(callback);
    }
  }

  /**
   * Emit event
   */
  emit(event, data) {
    if (event in this.listeners) {
      this.listeners[event].forEach(cb => {
        try {
          cb(data);
        } catch (err) {
          console.error(`Error in ${event} listener:`, err);
        }
      });
    }
  }

  /**
   * Disconnect
   */
  disconnect() {
    if (this.socket) {
      this.socket.close();
    }
  }
}

// ============================================================================
// USAGE EXAMPLE
// ============================================================================

async function example() {
  // Initialize client
  const client = new LLMChatClient('ws://localhost:8000');

  // Setup listeners
  let fullResponse = '';

  client.on('connected', () => {
    console.log('📡 Ready to send messages');
  });

  client.on('delta', (token) => {
    process.stdout.write(token);  // Stream tokens to console
    fullResponse += token;
  });

  client.on('done', (event) => {
    console.log('\n\n📊 Metadata:');
    console.log(`   Tokens: ${event.usage.totalTokens}`);
    console.log(`   Cost: $${event.usage.cost.totalCost}`);
    console.log(`   Message ID: ${event.message_id}`);
  });

  client.on('error', (error) => {
    console.error('❌ Error:', error.message);
  });

  client.on('disconnected', (event) => {
    if (event.code === 4001) {
      console.error('   → Check your JWT token');
    }
  });

  try {
    // Connect to server
    await client.connect();

    // Send message
    client.sendMessage({
      conversationId: '4f4e964e-812e-4621-8b43-c1d6e4d5f8a2',
      content: 'Explain quantum computing in 2 sentences',
      modelSlug: 'gpt-4-turbo'  // optional
    });

  } catch (err) {
    console.error('Failed to connect:', err.message);
  }
}

// Run if executed directly
if (typeof require !== 'undefined' && require.main === module) {
  example().catch(console.error);
}

// Export for use as module
if (typeof module !== 'undefined' && module.exports) {
  module.exports = LLMChatClient;
}

// ============================================================================
// NODE.JS CLI TEST
// ============================================================================

/*
Example Node.js WebSocket test:

const WebSocket = require('ws');

async function testWSNode() {
  const ws = new WebSocket('ws://localhost:8000/ws/chat/', {
    headers: {
      'Authorization': 'Bearer <your-jwt-token>'
    }
  });

  ws.on('open', () => {
    console.log('Connected');
    ws.send(JSON.stringify({
      type: 'send',
      payload: {
        conversation_id: '<conversation-uuid>',
        content: 'Hello, how are you?',
        model_slug: 'gpt-4'
      }
    }));
  });

  ws.on('message', (data) => {
    const msg = JSON.parse(data);
    if (msg.type === 'assistant.delta') {
      process.stdout.write(msg.delta);
    } else if (msg.type === 'assistant.done') {
      console.log('\n\nDone!', msg.usage);
    } else if (msg.type === 'assistant.error') {
      console.error('\nError:', msg.error);
    }
  });

  ws.on('error', console.error);
}

testWSNode();
*/

// ============================================================================
// CURL TEST
// ============================================================================

/*
To test with websocat (install: brew install websocat):

websocat "ws://localhost:8000/ws/chat/" \
  --header "Authorization: Bearer <your-jwt-token>"

Then send:
{
  "type": "send",
  "payload": {
    "conversation_id": "<uuid>",
    "content": "Hello!",
    "model_slug": "gpt-4"
  }
}

Response:
{"type": "assistant.delta", "delta": "Hello"}
{"type": "assistant.delta", "delta": " there"}
{"type": "assistant.done", "message_id": "...", "usage": {...}}
*/
