import json
import threading
import time

from fastapi import HTTPException
from groq import APIError, Groq
from pydantic import ValidationError

from app.config import settings
from app.db import get_supabase_client
from app.models.enums import LogAction, LogStatus
from app.models.schemas import (
    AICommandResponse,
    AICreateVM,
    AIDeleteVM,
    AIStartVM,
    AIStopVM,
    VMCreate,
)
from app.services import vm_service
from app.utils.logger import logger

GROQ_MODEL = "llama-3.3-70b-versatile"

ALLOWED_ACTIONS = {"create_vm", "start_vm", "stop_vm", "delete_vm"}

ACTION_SCHEMAS = {
    "create_vm": AICreateVM,
    "start_vm": AIStartVM,
    "stop_vm": AIStopVM,
    "delete_vm": AIDeleteVM,
}

SYSTEM_PROMPT = """\
You are a virtual machine management assistant for myVMS. You receive natural language \
commands and respond with EXACTLY ONE JSON object. Do not include any text outside the \
JSON object. Do not wrap the JSON in markdown code fences.

Available actions:

1. create_vm - Create a new virtual machine
   Format: {{"action": "create_vm", "name": "<vm-name>", "os": "<os-label>", "ram": <ram-in-mb>}}
   Rules: name is 1-50 chars (letters, numbers, hyphens, spaces). ram is 512-16384.

2. start_vm - Start a stopped or errored VM
   Format: {{"action": "start_vm", "vm_id": "<uuid>"}}

3. stop_vm - Stop a running VM
   Format: {{"action": "stop_vm", "vm_id": "<uuid>"}}

4. delete_vm - Delete a stopped VM
   Format: {{"action": "delete_vm", "vm_id": "<uuid>"}}

If the request is unclear or not about VM management, respond:
{{"action": "error", "message": "<brief explanation>"}}

The user currently has these VMs:
{vm_list_json}"""

# In-memory rate limit store: user_id -> list of timestamps.
# Single-process only — for multi-worker production, replace with Redis-backed store.
_rate_limit_store: dict[str, list[float]] = {}
_rate_limit_lock = threading.Lock()

RATE_LIMIT_MAX = 10
RATE_LIMIT_WINDOW = 60  # seconds


def _check_rate_limit(user_id: str) -> None:
    now = time.time()
    with _rate_limit_lock:
        timestamps = _rate_limit_store.get(user_id, [])
        timestamps = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]

        if len(timestamps) >= RATE_LIMIT_MAX:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded — max 10 AI commands per minute",
            )

        timestamps.append(now)
        _rate_limit_store[user_id] = timestamps


def _build_system_prompt(user_id: str) -> str:
    vms = vm_service.list_vms(user_id)
    vm_list = [
        {
            "id": str(vm.id),
            "name": vm.name,
            "status": vm.status.value,
            "os": vm.os,
            "ram": vm.ram,
        }
        for vm in vms
    ]
    return SYSTEM_PROMPT.format(vm_list_json=json.dumps(vm_list, indent=2))


def _call_groq(system_prompt: str, user_prompt: str) -> tuple[str, int]:
    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_tokens=256,
        )
    except APIError:
        raise HTTPException(status_code=503, detail="AI service unavailable") from None

    raw_text = response.choices[0].message.content or ""
    tokens = response.usage.total_tokens if response.usage else 0
    return raw_text, tokens


def _validate_ai_response(raw_json: str) -> dict:
    try:
        parsed = json.loads(raw_json)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(
            status_code=400,
            detail="AI returned an invalid response — please rephrase your command",
        ) from None

    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=400,
            detail="AI returned an invalid response — please rephrase your command",
        )

    action = parsed.get("action")

    if action == "error":
        raise HTTPException(
            status_code=400,
            detail=parsed.get("message", "AI could not understand your command"),
        )

    if action not in ALLOWED_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail="AI returned an invalid response — please rephrase your command",
        )

    schema = ACTION_SCHEMAS[action]
    try:
        validated = schema.model_validate(parsed)
    except ValidationError:
        raise HTTPException(
            status_code=400,
            detail="AI returned invalid parameters — please rephrase your command",
        ) from None

    return validated.model_dump(mode="json")


def _execute_action(validated: dict, user_id: str) -> str:
    action = validated["action"]

    if action == "create_vm":
        data = VMCreate(
            name=validated["name"], os=validated["os"], ram=validated["ram"]
        )
        vm = vm_service.create_vm(data, user_id)
        return f"Created VM '{vm.name}'"

    vm_id = str(validated["vm_id"])

    if action == "start_vm":
        vm = vm_service.start_vm(vm_id, user_id)
        return f"Started VM '{vm.name}'"

    if action == "stop_vm":
        vm = vm_service.stop_vm(vm_id, user_id)
        return f"Stopped VM '{vm.name}'"

    if action == "delete_vm":
        vm_service.delete_vm(vm_id, user_id)
        return "Deleted VM"

    raise HTTPException(status_code=400, detail="Unknown action")


def _log_ai_usage(user_id: str, prompt: str, response: str, tokens: int) -> None:
    try:
        supabase = get_supabase_client()
        supabase.table("ai_usage").insert(
            {
                "user_id": user_id,
                "prompt": prompt,
                "response": response,
                "tokens": tokens,
            }
        ).execute()
    except Exception as exc:  # noqa: BLE001
        logger.log(
            LogAction.ai_command,
            "ai",
            LogStatus.failure,
            f"ai_usage insert failed: {exc}",
            user_id,
        )


def _log_action(user_id: str, target: str, status: LogStatus, message: str) -> None:
    try:
        supabase = get_supabase_client()
        supabase.table("logs").insert(
            {
                "user_id": user_id,
                "action": LogAction.ai_command,
                "target": target,
                "status": status,
                "message": message,
            }
        ).execute()
        logger.log(LogAction.ai_command, target, status, message, user_id)
    except Exception as exc:  # noqa: BLE001
        logger.log(
            LogAction.ai_command,
            target,
            LogStatus.failure,
            f"Log insert failed: {exc}",
            user_id,
        )


def process_ai_command(prompt: str, user_id: str) -> AICommandResponse:
    _check_rate_limit(user_id)

    system_prompt = _build_system_prompt(user_id)
    raw_response, tokens = _call_groq(system_prompt, prompt)

    try:
        validated = _validate_ai_response(raw_response)
        result_message = _execute_action(validated, user_id)
    except HTTPException:
        _log_ai_usage(user_id, prompt, raw_response, tokens)
        _log_action(user_id, "ai", LogStatus.failure, raw_response[:500])
        raise

    _log_ai_usage(user_id, prompt, raw_response, tokens)
    _log_action(
        user_id, validated.get("vm_id", "ai"), LogStatus.success, result_message
    )

    return AICommandResponse(
        action=validated["action"],
        result=result_message,
        ai_response=validated,
    )
