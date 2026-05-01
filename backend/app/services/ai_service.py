import json
import threading
import time

from fastapi import HTTPException
from groq import APIError, APITimeoutError, Groq
from pydantic import ValidationError

from app.config import settings
from app.db import get_supabase_client
from app.models.enums import LogAction, LogStatus
from app.models.schemas import (
    AIChat,
    AICommandResponse,
    AICreateVM,
    AIDeleteVM,
    AIListVMs,
    AIQueryAnalytics,
    AIStartVM,
    AIStopVM,
    VMCreate,
)
from app.services import analytics_service, vm_service
from app.utils.logger import logger

GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
GROQ_TIMEOUT_SECONDS = 30.0

ALLOWED_ACTIONS = {
    "create_vm",
    "start_vm",
    "stop_vm",
    "delete_vm",
    "list_vms",
    "query_analytics",
    "chat",
}

ACTION_SCHEMAS = {
    "create_vm": AICreateVM,
    "start_vm": AIStartVM,
    "stop_vm": AIStopVM,
    "delete_vm": AIDeleteVM,
    "list_vms": AIListVMs,
    "query_analytics": AIQueryAnalytics,
    "chat": AIChat,
}

SYSTEM_PROMPT = """\
You are a virtual machine management assistant for myVMS. You receive natural language \
commands and respond with EXACTLY ONE JSON object. Do not include any text outside the \
JSON object. Do not wrap the JSON in markdown code fences.

The user currently has these VMs (use this data to resolve all VM references):
{vm_list_json}

Available actions:

1. create_vm - Create a new virtual machine
   Format: {{"action": "create_vm", "name": "<vm-name>", "os": "<os-label>", "ram": <ram-in-mb>, "cpu": <cores>, "disk_size": <mb>}}
   Rules: name is 1-50 chars (letters, numbers, hyphens, spaces). ram is 512-16384. cpu is 1-32 (optional, default 2). disk_size is 5120-512000 MB (optional, default 20480).
   OS default: if the user does not specify an OS, use "linux". Never leave os empty.
   IMPORTANT: if the user expresses intent to create a VM but has NOT provided a name, use "chat" to ask for the VM name and OS before acting. Do not invent a name.
   Synonyms: "spin up", "make", "build", "launch a new vm".

2. start_vm - Start a stopped or errored VM
   Format: {{"action": "start_vm", "vm_id": "<uuid>"}}

3. stop_vm - Stop a running VM
   Format: {{"action": "stop_vm", "vm_id": "<uuid>"}}

4. delete_vm - Delete a stopped OR error VM (both statuses are allowed)
   Format: {{"action": "delete_vm", "vm_id": "<uuid>"}}
   Synonyms: "drop", "remove", "destroy", "get rid of".

5. list_vms - List the user's VMs with their names, status, OS, and RAM
   Format: {{"action": "list_vms"}}
   Use this when the user asks to list VMs, see their VMs, or asks about specific VM names/details/status.
   Examples: "list my vms", "show my vms", "what vms do I have", "which vm is running/stopped/error", \
"what's the name of my vms", "show vm details".

6. query_analytics - Answer aggregate count / statistics questions ONLY
   Format: {{"action": "query_analytics", "message": "<ignored>"}}
   Use ONLY when the user asks for totals or counts: "how many vms do I have", \
"how many running vms", "how many AI commands have I used". Do NOT use for listing VMs or identifying VMs.

7. chat - Respond to general conversation or questions not related to VM actions
   Format: {{"action": "chat", "message": "<your response in natural language>"}}
   Use this for: general questions ("what is Ubuntu?", "which OS should I pick?", \
"where are my VMs created?", "what environments can I use?"), greetings, follow-up \
"why?" questions, or anything that does not require a VM action or analytics lookup.
   VMs are created and run on the local VirtualBox host machine. Use this fact when \
answering "where" questions about VM creation or storage.

If the request is genuinely harmful, adversarial, or completely unresolvable, respond:
{{"action": "error", "message": "<brief explanation>"}}

IMPORTANT RULES:

VM REFERENCE RESOLUTION — always resolve before acting:
- If there is exactly ONE VM in the list, then "it", "that", "the vm", "the remaining one", \
"the only one", "that one" all refer to that single VM. Use its id directly.
- If there are multiple VMs, resolve by name match first, then by status \
("the running vm", "the stopped vm", "the error vm"). If still ambiguous, use "chat" to ask which one.
- Never say a reference is ambiguous when there is only one VM.

COMMAND SYNONYMS — treat these as equivalent:
- delete / drop / remove / destroy / get rid of → delete_vm
- start / boot / launch / run → start_vm
- stop / halt / shut down / power off → stop_vm
- list / show / display / what vms → list_vms

STATE RULES:
- delete_vm works on VMs with status "stopped" OR "error". Delete error VMs directly — \
do NOT tell the user to stop them first.
- start_vm works on "stopped" or "error" VMs (error = retry).
- stop_vm only works on "running" VMs. If asked to stop a non-running VM, use "chat" to explain.
- You can only perform ONE action per response.
- When the user says "delete them all", "stop them all", etc. — use "chat" to explain you can \
only act on one VM at a time, then ask which one to start with.

FOLLOW-UP QUESTIONS:
- If the user asks "why?", "why not?", "why can't I?" after a previous failure — use "chat" \
to explain the reason clearly in natural language. Never return an empty or generic response.

- Prefer "chat" over "error" for off-topic but harmless messages.
- Respond in the SAME LANGUAGE the user typed in."""

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
            "cpu": vm.cpu,
            "disk_size": vm.disk_size,
            **({"error_message": vm.error_message} if vm.error_message else {}),
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
            max_tokens=1024,
            timeout=GROQ_TIMEOUT_SECONDS,
        )
    except APITimeoutError:
        raise HTTPException(
            status_code=504, detail="AI service timed out — please try again"
        ) from None
    except APIError as e:
        logger.log(
            LogAction.ai_command,
            "groq",
            LogStatus.failure,
            f"Groq APIError: {e}",
            "system",
        )
        raise HTTPException(
            status_code=503, detail=f"AI service unavailable: {e}"
        ) from None

    if not getattr(response, "choices", None):
        raise HTTPException(status_code=503, detail="AI service unavailable")

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

    if not isinstance(action, str):
        raise HTTPException(
            status_code=400,
            detail="AI returned an invalid response — please rephrase your command",
        )

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

    if action == "chat":
        return validated["message"]

    if action == "list_vms":
        vms = vm_service.list_vms(user_id)
        if not vms:
            return "You have no VMs."
        lines = [f"- **{vm.name}** — {vm.status.value} | {vm.os} | {vm.ram} MB" for vm in vms]
        return "Your VMs:\n" + "\n".join(lines)

    if action == "create_vm":
        data = VMCreate(
            name=validated["name"],
            os=validated["os"] or "linux",
            ram=validated["ram"],
            cpu=validated.get("cpu", 2),
            disk_size=validated.get("disk_size", 20480),
        )
        vm = vm_service.create_vm(data, user_id)
        return (
            f"VM '{vm.name}' created ({vm.os}, {vm.ram} MB RAM, {vm.cpu} vCPU). "
            "To install an OS, go to the VMs page, open the VM card, and use the "
            "'Attach ISO' button to attach your installation image — then start the VM."
        )

    if action == "query_analytics":
        supabase = get_supabase_client()
        profile_res = (
            supabase.table("profiles").select("is_admin").eq("id", user_id).execute()
        )
        is_admin = profile_res.data and profile_res.data[0].get("is_admin") is True
        if is_admin:
            a = analytics_service.get_admin_analytics()
            return (
                f"System-wide: {a.total_users} users, {a.total_vms} VMs "
                f"({a.running_vms} running, {a.stopped_vms} stopped, {a.error_vms} error), "
                f"{a.total_ai_commands} total AI commands."
            )
        a = analytics_service.get_user_analytics(user_id)
        return (
            f"You have {a.total_vms} VM{'s' if a.total_vms != 1 else ''} — "
            f"{a.running_vms} running, {a.stopped_vms} stopped"
            + (f", {a.error_vms} error" if a.error_vms > 0 else "")
            + f". You've used {a.total_ai_commands} AI commands total."
        )

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
