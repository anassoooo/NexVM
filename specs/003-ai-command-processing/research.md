# Research: AI Command Processing

**Branch**: `003-ai-command-processing` | **Date**: 2026-04-07  
**Last amended**: 2026-04-15 — §7 added for free conversation mode modification

---

## 1. Groq API Integration

**Decision**: Use the `groq` Python SDK with `client.chat.completions.create()`. Force JSON-only output via the system prompt (not the `response_format` parameter, which not all models support).

**Model selection**: `llama-3.3-70b-versatile` — fast, high-quality, reliable JSON output. Temperature 0 for deterministic responses. `max_tokens=256` is sufficient for any of the four action schemas (largest is create_vm at ~80 tokens).

**Implementation pattern**:

```python
from groq import Groq, APIError

def _call_groq(system_prompt: str, user_prompt: str) -> tuple[str, int]:
    client = Groq(api_key=settings.GROQ_API_KEY)
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0,
            max_tokens=256,
        )
    except APIError:
        raise HTTPException(503, "AI service unavailable") from None

    raw_text = response.choices[0].message.content or ""
    tokens   = response.usage.total_tokens if response.usage else 0
    return raw_text, tokens
```

**Token tracking**: `response.usage.total_tokens` gives the combined prompt + completion token count. Stored in `ai_usage.tokens` for cost monitoring.

**Alternatives considered**:
- `response_format={"type": "json_object"}` — only supported by some Groq models, not `llama-3.3-70b-versatile`. Rejected.
- OpenAI SDK — not used in this project. Groq SDK already in requirements.txt.
- Streaming — unnecessary for MVP, adds complexity. Rejected.

---

## 2. System Prompt Design

**Decision**: Static template with one dynamic section — the user's current VM list injected as a JSON array. The prompt enforces JSON-only output through instruction, includes all four action schemas, and provides an explicit error action for unrecognized commands.

**Key design choices**:
- Injecting the VM list enables name-to-UUID resolution ("start my Ubuntu VM" → correct vm_id) without a separate lookup step.
- The `{"action": "error", "message": "..."}` escape hatch lets the model signal unrecognized requests without producing malformed JSON.
- Using double braces `{{` and `}}` in the Python template string to escape the JSON examples.
- Temperature 0 ensures the model doesn't hallucinate UUIDs — it can only use UUIDs from the injected list.

**Prompt structure**:
```
[Role + output constraint]
[4 action schemas with examples]
[Error action format]
[User's current VM list as JSON]
```

**Failure modes and mitigations**:
- Model ignores instructions and returns markdown → `json.loads()` fails → 400 returned, usage logged.
- Model invents a UUID not in the list → `vm_service.get_vm_or_404` returns 404 → surfaced to user.
- Model returns empty string → `json.loads("")` raises → 400 returned.

---

## 3. AI Response Validation

**Decision**: Two-layer validation. First: `json.loads()` to catch non-JSON. Second: Pydantic `model_validate()` with per-action schemas using `Literal` types for the `action` field.

**Validation order**:
1. `json.loads(raw)` — reject non-JSON with 400
2. Check `parsed.get("action")` — reject unknown actions with 400; handle `"error"` action with 400 + AI message
3. `ActionSchema.model_validate(parsed)` — reject invalid parameters (RAM out of range, bad name regex, missing fields) with 400

**Using `Literal` types**:
```python
class AIStartVM(BaseModel):
    action: Literal["start_vm"]
    vm_id: uuid.UUID
```

`model_dump(mode="json")` returns UUIDs as strings, making the result directly JSON-serializable for the `AICommandResponse.ai_response` field.

**Alternatives considered**:
- Discriminated union (`Union[AICreateVM, AIStartVM, ...]`) — elegant but generates complex Pydantic errors that are harder to map to user-friendly messages. Rejected in favor of explicit action dispatch.

---

## 4. Rate Limiting

**Decision**: In-memory sliding window counter. Module-level `dict[str, list[float]]` mapping user_id to a list of Unix timestamps. Prune entries older than 60 seconds on each request, reject if count >= 10.

```python
_rate_limit_store: dict[str, list[float]] = {}

def _check_rate_limit(user_id: str) -> None:
    now = time.time()
    ts = [t for t in _rate_limit_store.get(user_id, []) if now - t < 60]
    if len(ts) >= 10:
        raise HTTPException(429, "Rate limit exceeded — max 10 AI commands per minute")
    ts.append(now)
    _rate_limit_store[user_id] = ts
```

**Limitations**: Resets on server restart. Not shared across multiple backend processes. Both are acceptable for single-tenant MVP.

**Alternatives considered**:
- Redis with sliding window — correct for multi-process/distributed. Overkill for single-tenant. Rejected.
- FastAPI middleware (e.g., `slowapi`) — adds a dependency for one endpoint. Rejected; inline function is simpler.

---

## 5. Dual Logging Strategy

**Decision**: Log to both `ai_usage` (AI-specific) and `logs` (general audit trail) before returning the HTTP response.

**`ai_usage` record**: prompt text, raw Groq response, token count, user_id. Written on every call — including failures (the raw error response is stored).

**`logs` record**: action=`ai_command`, target=vm_id or "ai", status=success/failure, message=result or error. Follows the same pattern as all other VM service logs.

**Failure ordering**: Both log calls are wrapped in try/except. If logging fails, the main operation result is still returned — logging failures do not cascade.

**Why both tables**: `ai_usage` tracks AI-specific data (tokens, raw LLM output) for cost monitoring and debugging. `logs` provides a unified audit trail across all actions (VM ops + AI ops) for admin review.

---

## 6. Frontend Chat Architecture

**Decision**: Client component with local message state. No conversation history sent to the backend or Groq — each submission is a fresh, independent request.

**Message state shape**:
```typescript
interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  action?: string;   // e.g. "create_vm" — shown as a badge
  error?: boolean;   // renders in red
}
```

**UX decisions**:
- Session-local history (not persisted) — the chat shows all messages since page load, cleared on refresh.
- "Thinking..." indicator during API call.
- Error messages displayed as assistant messages in red — same position as normal responses.
- 500-char limit enforced at input + visible counter.
- Each message is independent — no "context" from prior messages is sent to Groq.

**Alternatives considered**:
- Server component with form actions — simpler but no loading state or local history without client JS. Rejected.
- Persisted history via `GET /api/v1/ai/history` — deferred. `ai_usage` table exists but no route for MVP.

---

## 7. Free Conversation Mode (Modification — 2026-04-15)

**Context**: The original spec treats all non-VM messages as `{"action": "error", ...}`, forcing an HTTP 400. Users had no way to ask general questions, get help, or hold a natural conversation. The modification extends the AI to respond conversationally when no VM action is needed.

**Decision**: Add a `chat` action to the JSON contract. When the user's intent is not a VM operation, the LLM returns:

```json
{"action": "chat", "message": "<free-form natural language response>"}
```

The `message` field is displayed in the chat as the AI's reply. The JSON wrapper is validated by a `AIChat` Pydantic schema (`action: Literal["chat"]`, `message: str`) before the message reaches the frontend — no string escapes validation.

**Rationale**:
- Constitution §IV requires JSON-only output; this preserves the contract while enabling free-form text inside a validated field.
- Constitution §I prohibits free-form strings reaching any execution layer; `chat` has no execution path — the service reads `message` and returns it as-is.
- No new database tables, endpoints, or services are required — fully additive on top of the existing pipeline.

**Impact on `error` action**: The `error` action is retained for truly unresolvable requests (e.g., adversarial inputs, ambiguous multi-intent prompts). However, the system prompt is updated so the LLM uses `chat` as the default for general conversation and reserves `error` only for requests it genuinely cannot respond to safely.

**Token budget**: The current `max_tokens=256` is tight for conversational responses that may span several sentences. Bumped to `512`. JSON action schemas (the largest being `create_vm` at ~80 tokens) are unaffected; the increase only benefits `chat` responses.

**Rate limiting**: `chat` actions pass through the same 10-per-minute rate limiter. Conversational turns still invoke the Groq API and should be subject to the same abuse protection.

**Logging**: `chat` calls are logged to `ai_usage` (prompt + response + tokens) for observability. A `logs` entry with `target="ai"` and `status=success` is written. This keeps the audit trail consistent with all other AI actions.

**Alternatives considered**:
- Relaxing the JSON requirement (allow free-form LLM output) — rejected; violates §IV of the constitution. No exception path.
- Separate `/api/v1/ai/chat` endpoint — rejected; YAGNI. Adds a route, a new service branch, and splits concerns that the single-dispatch pipeline already handles cleanly.
- Discriminated union with `Union[AIAction, AIChat]` — considered but the explicit `action` dispatch table already in place is simpler. Adding `chat` to the existing dict requires one schema class and one line in `_execute_action`.
