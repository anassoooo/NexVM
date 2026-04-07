# Contract: AI Command API

**Branch**: `003-ai-command-processing` | **Date**: 2026-04-07

This contract defines the AI command endpoint — its request/response shape, status codes, and error responses. Future feature plans that call the AI endpoint must conform to this contract.

---

## Auth

All endpoints require:

```http
Authorization: Bearer <access_token>
```

Where `<access_token>` is a valid, non-expired Supabase JWT. Missing or invalid tokens return HTTP 401.

---

## Endpoints

### POST /api/v1/ai/command

Submit a natural language command. The system interprets it via Groq LLM, validates the result, and executes the corresponding VM action.

**Request body**:

```json
{
  "prompt": "create an Ubuntu VM with 4GB RAM"
}
```

| Field  | Type   | Required | Constraints      |
|--------|--------|----------|------------------|
| prompt | string | YES      | 1–500 characters |

**Success response** — HTTP 200:

```json
{
  "action":      "create_vm",
  "result":      "Created VM 'ubuntu-vm'",
  "ai_response": {
    "action": "create_vm",
    "name":   "ubuntu-vm",
    "os":     "Ubuntu",
    "ram":    4096
  }
}
```

| Field       | Type   | Description                                          |
|-------------|--------|------------------------------------------------------|
| action      | string | The action that was executed                         |
| result      | string | Human-readable result message                        |
| ai_response | object | The validated, JSON-serialized AI action parameters  |

**`ai_response` shapes by action**:

```json
// create_vm
{ "action": "create_vm", "name": "string", "os": "string", "ram": 2048 }

// start_vm / stop_vm / delete_vm
{ "action": "start_vm", "vm_id": "uuid-string" }
```

**Error responses**:

| Scenario                            | Status | Body                                                                    |
|-------------------------------------|--------|-------------------------------------------------------------------------|
| Missing/invalid JWT                 | 401    | `{"detail": "Invalid or expired token"}`                                |
| Empty prompt or prompt > 500 chars  | 422    | Pydantic validation error body                                          |
| Rate limit exceeded                 | 429    | `{"detail": "Rate limit exceeded — max 10 AI commands per minute"}`     |
| AI returned non-JSON                | 400    | `{"detail": "AI returned an invalid response — please rephrase your command"}` |
| AI returned unknown action          | 400    | `{"detail": "AI returned an invalid response — please rephrase your command"}` |
| AI returned error action            | 400    | `{"detail": "<AI's explanation message>"}`                              |
| AI returned invalid parameters      | 400    | `{"detail": "AI returned invalid parameters — please rephrase your command"}` |
| Groq API unavailable                | 503    | `{"detail": "AI service unavailable"}`                                  |
| VM not found (passthrough)          | 404    | `{"detail": "VM not found"}`                                            |
| VM in wrong state (passthrough)     | 409    | `{"detail": "VM is already in a transitional state"}` (or similar)     |
| VM service error (passthrough)      | 500    | `{"detail": "VBoxManage failed: <stderr>"}`                             |

---

## Rate Limiting

- **Limit**: 10 requests per 60-second sliding window per authenticated user
- **Scope**: Per user_id extracted from JWT — not per IP
- **Reset**: Sliding window (not fixed window) — the limit resets 60 seconds after the oldest request in the window
- **Response on limit**: HTTP 429 with `{"detail": "Rate limit exceeded — max 10 AI commands per minute"}`
- **Implementation**: In-memory (resets on server restart)

---

## Common Patterns

All 4xx/5xx responses share the shape:

```json
{ "detail": "<human-readable message>" }
```

VM service errors (404, 409, 500, 503) are passed through unchanged — the AI layer does not alter their status codes or messages. This means clients can handle AI-triggered VM errors the same way as direct VM endpoint errors.

---

## Logging Guarantees

Every call to `POST /api/v1/ai/command` produces:

1. One record in `ai_usage` table — prompt, raw Groq response, token count
2. One record in `logs` table — action=`ai_command`, target=vm_id or "ai", status=success/failure

Both records are written before the HTTP response is returned. If logging fails, the main response is still returned (logging failures do not cascade).
