# API Reference

omagent provides a FastAPI server with REST, SSE, and WebSocket endpoints for building web UIs and integrations.

## Starting the Server

```bash
omagent serve [--host 0.0.0.0] [--port 8000] [--pack default]
```

## Authentication

When `OMAGENT_API_KEY` is set, all endpoints require a Bearer token:

```
Authorization: Bearer your-api-key
```

If `OMAGENT_API_KEY` is not set, authentication is disabled (development mode).

## Endpoints

### Chat

#### `POST /chat`

Send a message and receive a complete (non-streaming) response.

**Request:**

```json
{
  "message": "What files are in the current directory?",
  "session_id": "optional-session-id",
  "pack": "default"
}
```

**Response:**

```json
{
  "session_id": "generated-or-provided-id",
  "response": "Here are the files in the current directory:\n- main.py\n- README.md",
  "tool_calls": [
    {
      "id": "toolu_abc123",
      "name": "list_dir",
      "input": {"path": "."}
    },
    {
      "id": "toolu_abc123",
      "name": "list_dir",
      "result": {"output": "main.py\nREADME.md"},
      "type": "result"
    }
  ]
}
```

#### `POST /stream`

Send a message and receive Server-Sent Events (SSE) as the agent works.

**Request:** Same as `/chat`.

**Response:** `text/event-stream` with events:

```
id: 0
event: text_delta
data: {"type": "text_delta", "content": "Let me ", "session_id": "abc123"}

id: 1
event: text_delta
data: {"type": "text_delta", "content": "check that.", "session_id": "abc123"}

id: 2
event: tool_call
data: {"type": "tool_call", "tool_call": {"id": "toolu_1", "name": "list_dir", "input": {"path": "."}}, "session_id": "abc123"}

id: 3
event: tool_result
data: {"type": "tool_result", "tool_result": {"id": "toolu_1", "name": "list_dir", "result": {"output": "main.py"}, "is_error": false}, "session_id": "abc123"}

id: 4
event: done
data: {"type": "done", "session_id": "abc123"}
```

**Event types:**

| Event | Description | Key Fields |
|-------|-------------|------------|
| `text_delta` | Streaming text chunk | `content` |
| `tool_call` | Agent is calling a tool | `tool_call.id`, `tool_call.name`, `tool_call.input` |
| `tool_result` | Tool execution result | `tool_result.id`, `tool_result.name`, `tool_result.result`, `tool_result.is_error` |
| `permission_prompt` | Tool needs user approval | `tool_name`, `input` |
| `permission_denied` | Tool was blocked | `tool_name`, `reason` |
| `error` | Something went wrong | `message` |
| `done` | Turn complete | -- |

#### `WS /ws/chat`

WebSocket endpoint for real-time bidirectional streaming.

**Send (JSON):**

```json
{
  "message": "Hello",
  "pack": "default",
  "session_id": "optional"
}
```

**Receive (JSON):** Same event format as SSE (without the `event:` / `data:` envelope).

The WebSocket maintains session state across messages. Send multiple messages on the same connection for multi-turn conversation.

### Sessions

#### `GET /sessions`

List recent sessions.

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | Maximum sessions to return |

**Response:**

```json
{
  "sessions": [
    {
      "id": "abc123",
      "pack_name": "data_science",
      "updated_at": "2026-04-03T15:30:00Z"
    }
  ]
}
```

#### `GET /sessions/{session_id}`

Get a specific session with its full message history.

#### `DELETE /sessions/{session_id}`

Delete a session.

#### `POST /sessions/{session_id}/fork`

Create a deep copy of a session with a new ID.

**Response:**

```json
{
  "forked_id": "new-session-id",
  "original_id": "abc123",
  "message_count": 12
}
```

#### `GET /sessions/{session_id}/export`

Export a session.

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `format` | string | `json` | `json` or `markdown` |

#### `POST /sessions/import`

Import a session from JSON. Send the session JSON as the request body.

#### `PATCH /sessions/{session_id}`

Update session metadata.

**Request:**

```json
{
  "pack_name": "flutter_dev"
}
```

### Tools and Permissions

#### `GET /tools`

List available tools for a pack.

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `pack` | string | server default | Pack name |

**Response:**

```json
{
  "tools": [
    {
      "name": "read_file",
      "description": "Read the contents of a file",
      "input_schema": { ... }
    }
  ],
  "pack": "default"
}
```

#### `POST /sessions/{session_id}/approve/{tool_call_id}`

Approve a pending tool execution (when permission is `prompt`).

#### `POST /sessions/{session_id}/deny/{tool_call_id}`

Deny a pending tool execution.

### Packs

#### `GET /packs`

List all available domain packs.

**Response:**

```json
{
  "packs": ["default", "data_science", "flutter_dev"]
}
```

### Observability

#### `GET /sessions/{session_id}/timeline`

Get chronological activity events.

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 100 | Maximum events |
| `event_types` | string | (all) | Comma-separated filter |

#### `GET /sessions/{session_id}/journal`

Get structured events from the JSONL event journal.

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 100 | Maximum events |
| `event_types` | string | (all) | Comma-separated filter |

#### `GET /sessions/{session_id}/artifacts`

List artifacts in a session workspace.

#### `GET /sessions/{session_id}/plan`

Get the current agent plan with step statuses.

#### `GET /sessions/{session_id}/memory`

Get persistent memories stored during the session.

#### `GET /activity/daily`

Get a daily activity report.

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `date` | string | today | `YYYY-MM-DD` format |

### Health

#### `GET /health`

Health check endpoint.

**Response:**

```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

## Error Responses

All errors follow this format:

```json
{
  "detail": "Session not found"
}
```

| Status Code | Meaning |
|-------------|---------|
| 400 | Bad request (invalid input) |
| 401 | Unauthorized (missing/invalid token) |
| 404 | Resource not found |
| 500 | Internal server error |

## Client Examples

### Python (httpx)

```python
import httpx

# Non-streaming
response = httpx.post("http://localhost:8000/chat", json={
    "message": "Hello",
    "pack": "default"
})
print(response.json()["response"])

# Streaming (SSE)
with httpx.stream("POST", "http://localhost:8000/stream", json={
    "message": "List files"
}) as response:
    for line in response.iter_lines():
        if line.startswith("data: "):
            import json
            event = json.loads(line[6:])
            if event["type"] == "text_delta":
                print(event["content"], end="")
```

### JavaScript (fetch)

```javascript
// Streaming with EventSource-like fetch
const response = await fetch("http://localhost:8000/stream", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ message: "Hello" }),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const text = decoder.decode(value);
  // Parse SSE events from text
}
```

### cURL

```bash
# Non-streaming
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'

# Streaming
curl -N -X POST http://localhost:8000/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'

# With auth
curl -H "Authorization: Bearer your-key" \
  http://localhost:8000/health
```
