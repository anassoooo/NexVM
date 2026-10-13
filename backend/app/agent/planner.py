"""The planning loop: the model reads with tools and proposes writes; code decides (§XIV.1).

Read calls execute. Write calls are validated (Pydantic), simulated against a copy of the
user's world and, if both pass, queued as plan steps. Every rejection goes back to the model
as a tool error so it can correct itself. The loop is bounded (§XIV.3) and traced (§XIV.5).
"""

import json
from dataclasses import asdict, dataclass, field

from pydantic import ValidationError

from app.agent import prompts
from app.agent import tools as t
from app.agent.backend import VMBackend
from app.agent.diagnostics import Finding, diagnose
from app.agent.llm import LLM, LLMError
from app.agent.trace import Trace
from app.agent.world import SimulationError, Simulator, validate_args

MAX_TURNS = 8
MAX_STEPS = 12
MAX_TOOL_CALLS = 24
HISTORY_TURNS = 6


@dataclass
class PlanStep:
    index: int
    tool: str
    args: dict
    risk: str
    description: str
    effect: str
    status: str = "pending"  # pending | running | done | failed | skipped
    result: str = ""
    duration_ms: int = 0


@dataclass
class PlanResult:
    answer: str
    steps: list[PlanStep] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)
    trace: Trace = field(default_factory=Trace)
    stopped_reason: str = ""

    @property
    def needs_approval(self) -> bool:
        return bool(self.steps)

    def steps_json(self) -> list[dict]:
        return [asdict(s) for s in self.steps]


def _error(msg: str) -> str:
    return json.dumps({"error": msg})


def _format_validation(exc: ValidationError) -> str:
    return "; ".join(f"{'.'.join(map(str, e['loc'])) or 'arguments'}: {e['msg']}" for e in exc.errors())


class Planner:
    def __init__(self, llm: LLM, backend: VMBackend):
        self.llm = llm
        self.backend = backend

    def plan(
        self,
        user_id: str,
        prompt: str,
        history: list[tuple[str, str]] | None = None,
        repair_note: str | None = None,
        trace: Trace | None = None,
    ) -> PlanResult:
        trace = trace or Trace()
        world = self.backend.world(user_id)
        sim = Simulator(world)
        result = PlanResult(answer="", trace=trace)

        messages: list[dict] = [{"role": "system", "content": prompts.render(world)}]
        for past_prompt, past_answer in (history or [])[-HISTORY_TURNS:]:
            messages += [{"role": "user", "content": past_prompt},
                         {"role": "assistant", "content": past_answer or "(no reply)"}]
        user_msg = prompt if not repair_note else f"{prompt}\n\n[Execution update]\n{repair_note}"
        messages.append({"role": "user", "content": user_msg})

        tool_calls_used = 0
        schemas = t.tool_schemas()
        for _turn in range(MAX_TURNS):
            with trace.span("llm", self.llm.model) as span:
                try:
                    reply = self.llm.complete(messages, schemas)
                except LLMError as exc:
                    span.ok, span.detail = False, str(exc)
                    result.answer = f"{exc}. Please try again."
                    result.stopped_reason = "llm_error"
                    return result
                span.tokens_in, span.tokens_out = reply.tokens_in, reply.tokens_out
                span.detail = (", ".join(c.name for c in reply.tool_calls) or reply.content)[:200]
            messages.append(reply.as_message())

            if not reply.tool_calls:
                result.answer = reply.content.strip()
                break

            all_writes_accepted = True
            for call in reply.tool_calls:
                tool_calls_used += 1
                if tool_calls_used > MAX_TOOL_CALLS:
                    output = _error("Tool call budget used up. Stop calling tools and reply to the user.")
                else:
                    output = self._handle(call.name, call.arguments, user_id, world, sim, result, trace)
                spec = t.TOOLS.get(call.name)
                if spec is None or spec.kind == t.Kind.read or '"error"' in output[:12]:
                    all_writes_accepted = False
                messages.append({"role": "tool", "tool_call_id": call.id, "content": output})

            # The model already wrote its reply alongside the calls and nothing needs another
            # look: skip the extra summary turn (saves ~2k tokens per plan).
            if all_writes_accepted and reply.content.strip():
                result.answer = reply.content.strip()
                break
        else:
            result.stopped_reason = "max_turns"

        if not result.answer and result.stopped_reason == "max_turns":
            result.answer = (
                f"I hit my planning limit before finishing. The {len(result.steps)} step(s) below are a "
                "partial plan; review them carefully or rephrase the request."
                if result.steps else "I hit my planning limit before finishing. Could you rephrase or narrow it down?"
            )
        if not result.answer:
            if result.steps:
                result.answer = f"I prepared a plan with {len(result.steps)} step(s). Review it and approve to run it."
            else:
                result.answer = "I couldn't finish working that out. Could you rephrase or narrow it down?"
        return result

    def _handle(self, name, raw_args, user_id, world, sim, result: PlanResult, trace: Trace) -> str:
        spec = t.TOOLS.get(name)
        with trace.span("tool", name) as span:
            if spec is None:
                span.ok, span.detail = False, "unknown tool"
                return _error(f"Unknown tool '{name}'")
            try:
                args = validate_args(name, json.loads(raw_args or "{}"))
            except (json.JSONDecodeError, ValidationError) as exc:
                msg = _format_validation(exc) if isinstance(exc, ValidationError) else "arguments are not valid JSON"
                span.ok, span.detail = False, msg
                return _error(f"Invalid arguments: {msg}")

            if spec.kind == t.Kind.read:
                out = self._read(name, args, user_id, world, result)
                span.detail = out[:200]
                return out

            if len(result.steps) >= MAX_STEPS:
                span.ok, span.detail = False, "plan too long"
                return _error(f"A plan can have at most {MAX_STEPS} steps. Stop adding steps.")
            try:
                effect = sim.apply(name, args)
            except SimulationError as exc:
                span.ok, span.detail = False, str(exc)
                return _error(f"Rejected: {exc}")
            dumped = args.model_dump()
            step = PlanStep(index=len(result.steps) + 1, tool=name, args=dumped, risk=spec.risk.value,
                            description=t.describe(name, dumped), effect=effect)
            result.steps.append(step)
            span.detail = f"queued step {step.index}: {step.description}"
            return json.dumps({"queued_step": step.index, "simulated_effect": effect,
                               "plan_so_far": [s.description for s in result.steps],
                               "note": "Not executed yet. Do not queue these steps again."})

    def _read(self, name, args, user_id, world, result: PlanResult) -> str:
        match name:
            case "list_vms":
                data = [vm.public() for vm in world.vms.values()]
            case "list_isos":
                data = world.isos
            case "get_quota":
                data = world.quota()
            case "recent_activity":
                data = self.backend.recent_activity(user_id, args.limit)
            case "diagnose_vm":
                vm = world.vms.get(args.vm)
                if vm is None:
                    return _error(f"No VM named '{args.vm}'. Existing VMs: {', '.join(world.vms) or 'none'}")
                findings: list[Finding] = diagnose(
                    vm, world, self.backend.metrics(user_id, vm), self.backend.recent_activity(user_id, 20)
                )
                result.findings += [f.to_dict() for f in findings]
                data = [f.to_dict() for f in findings]
            case _:
                return _error(f"Unknown read tool '{name}'")
        return json.dumps({"data": data}, default=str)
