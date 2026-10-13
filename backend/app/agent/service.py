"""Agent orchestration: plan → approve → execute → (repair) and run bookkeeping.

The executor never calls the model to act (§XIV.1): it replays the approved, validated steps
against the backend. The model is only consulted again to *propose* a repaired plan, which
needs a fresh approval.
"""

import threading
import time
import uuid
from dataclasses import asdict

from fastapi import HTTPException

from app.agent import tools as t
from app.agent.backend import StepError, VMBackend
from app.agent.llm import LLM
from app.agent.planner import HISTORY_TURNS, PlanResult, Planner
from app.agent.store import RunStore
from app.agent.trace import Trace
from app.agent.world import SimulationError, Simulator, validate_args

MAX_REPAIRS = 1
OPEN_STATUSES = ("needs_approval",)


def _history_entry(run: dict) -> tuple[str, str]:
    answer = run.get("answer") or ""
    if run.get("plan"):
        steps = "; ".join(f"{s['index']}. {s['description']} [{s['status']}]" for s in run["plan"])
        answer += f"\n(Plan {run['status']}: {steps})"
    return run["prompt"], answer


class AgentService:
    def __init__(self, llm: LLM, backend: VMBackend, store: RunStore, *, run_async: bool = True):
        self.llm, self.backend, self.store = llm, backend, store
        self.planner = Planner(llm, backend)
        self.run_async = run_async  # tests execute inline
        self._cancelled: set[str] = set()

    # ---------------------------------------------------------------- planning
    def start(self, user_id: str, prompt: str, conversation_id: str | None) -> dict:
        conversation_id = conversation_id or str(uuid.uuid4())
        previous = self.store.conversation(conversation_id, user_id, HISTORY_TURNS)
        for old in previous:  # a new message supersedes a plan still waiting for approval
            if old["status"] in OPEN_STATUSES and old.get("id"):
                self.store.update(old["id"], {"status": "cancelled", "error": "Superseded by a newer message"})
                old["status"] = "cancelled"
        result = self.planner.plan(user_id, prompt, [_history_entry(r) for r in previous])
        return self.store.create({
            "user_id": user_id, "conversation_id": conversation_id, "prompt": prompt,
            "status": "needs_approval" if result.needs_approval else "answered",
            "answer": result.answer, "plan": result.steps_json(), "plan_version": 1 if result.steps else 0,
            "findings": result.findings, "trace": result.trace.to_list(), "model": self.llm.model,
            "total_tokens": result.trace.tokens, "latency_ms": result.trace.elapsed_ms,
        })

    # ---------------------------------------------------------------- approval
    def approve(self, user_id: str, run_id: str, plan_version: int) -> dict:
        run = self._own(user_id, run_id)
        if run["status"] != "needs_approval":
            raise HTTPException(status_code=409, detail=f"Run is {run['status']}, not waiting for approval")
        if plan_version != run["plan_version"]:
            raise HTTPException(status_code=409, detail="The plan changed since you looked at it; review it again")
        run = self.store.update(run_id, {"status": "running"})
        if self.run_async:
            threading.Thread(target=self._execute_safely, args=(user_id, run_id), daemon=True).start()
        else:
            self._execute_safely(user_id, run_id)
            run = self.store.get(run_id, user_id)
        return run

    def cancel(self, user_id: str, run_id: str) -> dict:
        run = self._own(user_id, run_id)
        if run["status"] not in ("needs_approval", "running"):
            raise HTTPException(status_code=409, detail=f"Run is already {run['status']}")
        self._cancelled.add(run_id)
        plan = [{**s, "status": "skipped"} if s["status"] == "pending" else s for s in run["plan"]]
        return self.store.update(run_id, {"status": "cancelled", "plan": plan})

    def get(self, user_id: str, run_id: str) -> dict:
        return self._own(user_id, run_id)

    def list_runs(self, user_id: str, limit: int = 30) -> list[dict]:
        return self.store.list_runs(user_id, limit)

    def _own(self, user_id: str, run_id: str) -> dict:
        run = self.store.get(run_id, user_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return run

    # ---------------------------------------------------------------- execution
    def _execute_safely(self, user_id: str, run_id: str) -> None:
        try:
            self._execute(user_id, run_id)
        except Exception as exc:  # noqa: BLE001 — never leave a run stuck in 'running'
            self.store.update(run_id, {"status": "failed", "error": f"Internal error: {exc}"})

    def _execute(self, user_id: str, run_id: str) -> None:
        run = self.store.get(run_id, user_id)
        plan: list[dict] = run["plan"]
        trace_rows: list[dict] = list(run.get("trace") or [])
        offset = (trace_rows[-1]["start_ms"] + trace_rows[-1]["duration_ms"]) if trace_rows else 0
        trace = Trace()

        for step in plan:
            if step["status"] != "pending":
                continue
            if run_id in self._cancelled:
                return
            step["status"] = "running"
            self.store.update(run_id, {"plan": plan})
            started = time.perf_counter()
            with trace.span("step", step["tool"]) as span:
                try:
                    world = self.backend.world(user_id)
                    args = validate_args(step["tool"], step["args"])
                    Simulator(world).apply(step["tool"], args)  # re-check against today's state
                    step["result"] = self.backend.execute(user_id, step["tool"], args, world)
                    step["status"] = "done"
                    span.detail = step["result"]
                except (StepError, SimulationError) as exc:
                    step["status"], step["result"] = "failed", str(exc)
                    span.ok, span.detail = False, str(exc)
            step["duration_ms"] = int((time.perf_counter() - started) * 1000)
            self.store.update(run_id, {"plan": plan, "trace": trace_rows + trace.to_list(offset)})
            if step["status"] == "failed":
                self._repair(user_id, run, plan, step, trace_rows + trace.to_list(offset))
                return

        done = sum(s["status"] == "done" for s in plan)
        self.store.update(run_id, {"status": "completed", "answer": f"Done: {done} step(s) completed.",
                                   "trace": trace_rows + trace.to_list(offset)})

    def _repair(self, user_id: str, run: dict, plan: list[dict], failed: dict, trace_rows: list[dict]) -> None:
        for s in plan:
            if s["status"] == "pending":
                s["status"] = "skipped"
        if run.get("repairs", 0) >= MAX_REPAIRS:
            self.store.update(run["id"], {"status": "failed", "plan": plan,
                                          "error": f"Step {failed['index']} failed: {failed['result']}"})
            return

        done = [s for s in plan if s["status"] == "done"]
        note = (f"Step {failed['index']} ({failed['description']}) failed: {failed['result']}.\n"
                f"Already done: {'; '.join(s['description'] for s in done) or 'nothing'}.\n"
                "Plan only the remaining work toward the original request, using the current state.")
        offset = (trace_rows[-1]["start_ms"] + trace_rows[-1]["duration_ms"]) if trace_rows else 0
        result: PlanResult = self.planner.plan(user_id, run["prompt"], repair_note=note)
        new_steps = [{**asdict(s), "index": len(plan) + i + 1} for i, s in enumerate(result.steps)]
        fields = {
            "plan": plan + new_steps, "repairs": run.get("repairs", 0) + 1,
            "trace": trace_rows + result.trace.to_list(offset), "findings": run.get("findings", []) + result.findings,
            "total_tokens": run.get("total_tokens", 0) + result.trace.tokens,
            "error": f"Step {failed['index']} failed: {failed['result']}",
        }
        if new_steps:
            fields |= {"status": "needs_approval", "plan_version": run["plan_version"] + 1,
                       "answer": f"Step {failed['index']} failed ({failed['result']}). {result.answer}"}
        else:
            fields |= {"status": "failed", "answer": result.answer}
        self.store.update(run["id"], fields)


def risk_summary(plan: list[dict]) -> dict:
    """Counts by risk for pending steps (used by the API response)."""
    out = {r.value: 0 for r in t.Risk if r != t.Risk.none}
    for s in plan:
        if s["status"] == "pending":
            out[s["risk"]] = out.get(s["risk"], 0) + 1
    return out
