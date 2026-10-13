"""Spec 013 — deterministic agent tests: scripted LLM, in-memory backend and store."""

import json
from unittest.mock import patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.agent import tools as t
from app.agent.diagnostics import diagnose
from app.agent.llm import LLMError, LLMResponse, ToolCall
from app.agent.planner import MAX_STEPS, MAX_TURNS, Planner
from app.agent.service import AgentService
from app.agent.store import InMemoryRunStore
from app.agent.world import SimulationError, Simulator, validate_args
from app.dependencies import UserClaims, get_current_user
from app.routes import agent as agent_routes
from evals.fake_backend import FakeBackend, make_world

USER = "00000000-0000-0000-0000-000000000001"
OTHER = "00000000-0000-0000-0000-000000000002"


class ScriptedLLM:
    """Replays a list of responses; records the messages it was given."""

    model = "scripted"

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls: list[list[dict]] = []

    def complete(self, messages, tools):
        self.calls.append([dict(m) for m in messages])
        nxt = self.responses.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt


_n = 0


def call(tool_name, /, **args) -> ToolCall:
    global _n
    _n += 1
    return ToolCall(f"call_{_n}", tool_name, json.dumps(args))


def turn(*calls, content="") -> LLMResponse:
    return LLMResponse(content=content, tool_calls=list(calls), tokens_in=100, tokens_out=20)


def say(text) -> LLMResponse:
    return LLMResponse(content=text, tokens_in=100, tokens_out=10)


def tool_outputs(llm: ScriptedLLM, call_index: int) -> list[dict]:
    return [json.loads(m["content"]) for m in llm.calls[call_index] if m["role"] == "tool"]


@pytest.fixture
def backend():
    return FakeBackend(make_world(
        [{"name": "web", "status": "running"}, {"name": "db", "status": "stopped", "snapshots": ["s1"]}],
        ports_in_use={8080}, isos=["ubuntu.iso"],
    ), metrics={"web": {"cpu_percent": 20.0, "ram_used_mb": 1950}})


# ─── tools ────────────────────────────────────────────────────────────────


def test_no_tool_accepts_a_user_identity():
    for spec in t.TOOLS.values():
        props = spec.schema()["function"]["parameters"]["properties"]
        assert not any("user" in p or "owner" in p for p in props), spec.name


def test_write_tools_have_a_risk_level_and_read_tools_do_not():
    for spec in t.TOOLS.values():
        assert (spec.risk == t.Risk.none) == (spec.kind == t.Kind.read), spec.name


def test_write_args_reject_unknown_fields():
    with pytest.raises(Exception):
        validate_args("start_vm", {"vm": "web", "user_id": OTHER})


# ─── simulator ────────────────────────────────────────────────────────────


def _sim(**world):
    return Simulator(make_world(**world))


def test_simulator_state_flows_between_steps():
    sim = _sim(vms=[])
    sim.apply("create_vm", validate_args("create_vm", {"name": "a"}))
    sim.apply("start_vm", validate_args("start_vm", {"vm": "a"}))
    assert sim.world.vms["a"].status == "running"
    with pytest.raises(SimulationError, match="running"):
        sim.apply("start_vm", validate_args("start_vm", {"vm": "a"}))


def test_simulator_explains_duplicate_from_earlier_step():
    sim = _sim(vms=[])
    sim.apply("create_vm", validate_args("create_vm", {"name": "a"}))
    with pytest.raises(SimulationError, match="earlier step of this plan"):
        sim.apply("create_vm", validate_args("create_vm", {"name": "a"}))


def test_simulator_enforces_quotas():
    sim = _sim(vms=[{"name": "x"}], max_vms=1)
    with pytest.raises(SimulationError, match="VM quota"):
        sim.apply("create_vm", validate_args("create_vm", {"name": "b"}))
    sim = _sim(vms=[], disk_quota_mb=10000)
    with pytest.raises(SimulationError, match="Disk quota"):
        sim.apply("create_vm", validate_args("create_vm", {"name": "b", "disk_size": 20480}))


def test_simulator_suggests_next_free_port():
    sim = _sim(vms=[{"name": "a"}], ports_in_use={2201, 2202})
    with pytest.raises(SimulationError, match="next free port is 2203"):
        sim.apply("add_port_rule", validate_args("add_port_rule",
                  {"vm": "a", "rule_name": "ssh", "host_port": 2201, "guest_port": 22}))


def test_simulator_snapshot_and_iso_rules():
    sim = _sim(vms=[{"name": "a", "snapshots": ["s1"]}], isos=["u.iso"])
    with pytest.raises(SimulationError, match="no snapshot 's2'"):
        sim.apply("restore_snapshot", validate_args("restore_snapshot", {"vm": "a", "snapshot": "s2"}))
    with pytest.raises(SimulationError, match="No ISO named"):
        sim.apply("attach_iso", validate_args("attach_iso", {"vm": "a", "iso_file": "x.iso"}))
    sim.apply("attach_iso", validate_args("attach_iso", {"vm": "a", "iso_file": "u.iso"}))
    assert sim.world.vms["a"].iso_attached


def test_simulator_does_not_touch_the_source_world():
    world = make_world([{"name": "a"}])
    Simulator(world).apply("delete_vm", validate_args("delete_vm", {"vm": "a"}))
    assert "a" in world.vms


# ─── diagnostics ──────────────────────────────────────────────────────────


def test_diagnostics_memory_pressure_suggests_next_preset(backend):
    world = backend.world(USER)
    codes = {f.code: f for f in diagnose(world.vms["web"], world, {"ram_used_mb": 1950, "cpu_percent": 10}, [])}
    assert codes["memory_pressure"].severity == "warning"
    assert "4096" in codes["memory_pressure"].suggestion


def test_diagnostics_error_state_and_failures():
    world = make_world([{"name": "x", "status": "error", "error_message": "boot failed"}])
    activity = [{"target": "x", "status": "failure", "action": "start_vm", "message": "boom"}]
    codes = {f.code for f in diagnose(world.vms["x"], world, None, activity)}
    assert {"error_state", "recent_failures"} <= codes


def test_diagnostics_healthy():
    world = make_world([{"name": "x"}])
    assert [f.code for f in diagnose(world.vms["x"], world, None, [])] == ["healthy"]


# ─── planner ──────────────────────────────────────────────────────────────


def test_reads_execute_and_writes_are_queued_not_executed(backend):
    llm = ScriptedLLM(
        turn(call("list_vms")),
        turn(call("stop_vm", vm="web"), call("modify_vm", vm="web", ram=4096)),
        say("Queued: stop web, then resize it. Waiting for your approval."),
    )
    result = Planner(llm, backend).plan(USER, "give web 4 GB")
    assert [s.tool for s in result.steps] == ["stop_vm", "modify_vm"]
    assert result.steps[0].risk == "destructive"
    assert backend.executed == []  # nothing ran
    assert "web" in json.dumps(tool_outputs(llm, 1)[0]["data"])


def test_invalid_arguments_are_fed_back_and_corrected(backend):
    llm = ScriptedLLM(
        turn(call("create_vm", name="lab", ram=99999)),
        turn(call("create_vm", name="lab", ram=16384), content="Queued lab."),
    )
    result = Planner(llm, backend).plan(USER, "huge vm lab")
    assert "Invalid arguments" in tool_outputs(llm, 1)[0]["error"]
    assert [s.args["ram"] for s in result.steps] == [16384]


def test_simulation_errors_are_fed_back(backend):
    llm = ScriptedLLM(turn(call("modify_vm", vm="web", ram=4096)), say("web must be stopped first."))
    result = Planner(llm, backend).plan(USER, "resize web")
    assert result.steps == []
    assert "Rejected" in tool_outputs(llm, 1)[0]["error"]


def test_summary_turn_is_skipped_when_all_writes_accepted(backend):
    llm = ScriptedLLM(turn(call("create_vm", name="a"), call("start_vm", vm="a"), content="Queued a."))
    result = Planner(llm, backend).plan(USER, "create and start a")
    assert len(llm.calls) == 1
    assert result.answer == "Queued a."
    assert result.steps[0].effect == "'a' will exist (stopped)"


def test_turn_budget_gives_an_honest_partial_answer(backend):
    llm = ScriptedLLM(*[turn(call("list_vms")) for _ in range(MAX_TURNS)])
    result = Planner(llm, backend).plan(USER, "loop forever")
    assert result.stopped_reason == "max_turns"
    assert "planning limit" in result.answer


def test_plan_size_is_capped(backend):
    calls = [call("create_vm", name=f"n{i}", disk_size=5120) for i in range(MAX_STEPS + 2)]
    big = make_world([], max_vms=50)
    llm = ScriptedLLM(turn(*calls), say("done"))
    result = Planner(llm, FakeBackend(big)).plan(USER, "many")
    assert len(result.steps) == MAX_STEPS


def test_unknown_tool_and_llm_failure(backend):
    llm = ScriptedLLM(turn(call("rm_rf")), LLMError("The AI service timed out"))
    result = Planner(llm, backend).plan(USER, "x")
    assert "Unknown tool" in tool_outputs(llm, 1)[0]["error"]
    assert result.stopped_reason == "llm_error" and "timed out" in result.answer


def test_diagnose_tool_collects_findings(backend):
    llm = ScriptedLLM(turn(call("diagnose_vm", vm="web")), say("web is short on memory."))
    result = Planner(llm, backend).plan(USER, "why is web slow")
    assert any(f["code"] == "memory_pressure" for f in result.findings)


def test_trace_records_llm_and_tool_spans(backend):
    llm = ScriptedLLM(turn(call("list_vms")), say("You have 2 VMs."))
    result = Planner(llm, backend).plan(USER, "list")
    kinds = [s.kind for s in result.trace.spans]
    assert kinds == ["llm", "tool", "llm"]
    assert result.trace.tokens == 230


# ─── service: approve, execute, repair ────────────────────────────────────


def _service(backend, *responses):
    return AgentService(ScriptedLLM(*responses), backend, InMemoryRunStore(), run_async=False)


def test_full_flow_plan_approve_execute(backend):
    svc = _service(backend, turn(call("create_vm", name="a"), call("start_vm", vm="a"), content="Queued."))
    run = svc.start(USER, "create and start a", None)
    assert run["status"] == "needs_approval" and run["plan_version"] == 1
    assert backend.executed == []

    run = svc.approve(USER, run["id"], 1)
    assert run["status"] == "completed"
    assert [tool for tool, _ in backend.executed] == ["create_vm", "start_vm"]
    assert [s["status"] for s in run["plan"]] == ["done", "done"]
    assert [s["kind"] for s in run["trace"]].count("step") == 2


def test_answer_only_runs_need_no_approval(backend):
    svc = _service(backend, say("Ubuntu is a Linux distribution."))
    run = svc.start(USER, "what is ubuntu?", None)
    assert run["status"] == "answered"
    with pytest.raises(HTTPException) as exc:
        svc.approve(USER, run["id"], 1)
    assert exc.value.status_code == 409


def test_stale_plan_version_is_refused(backend):
    svc = _service(backend, turn(call("start_vm", vm="db"), content="Queued."))
    run = svc.start(USER, "start db", None)
    with pytest.raises(HTTPException) as exc:
        svc.approve(USER, run["id"], 2)
    assert exc.value.status_code == 409


def test_other_users_cannot_see_or_approve(backend):
    svc = _service(backend, turn(call("start_vm", vm="db"), content="Queued."))
    run = svc.start(USER, "start db", None)
    for action in (lambda: svc.get(OTHER, run["id"]), lambda: svc.approve(OTHER, run["id"], 1),
                   lambda: svc.cancel(OTHER, run["id"])):
        with pytest.raises(HTTPException) as exc:
            action()
        assert exc.value.status_code == 404


def test_failed_step_triggers_one_repair_needing_new_approval(backend):
    backend.failures = {"add_port_rule": "Host port 2222 is already used by another VM"}
    svc = _service(
        backend,
        turn(call("add_port_rule", vm="db", rule_name="ssh", host_port=2222, guest_port=22),
             call("start_vm", vm="db"), content="Queued."),
        # repair planning
        turn(call("add_port_rule", vm="db", rule_name="ssh", host_port=2223, guest_port=22),
             call("start_vm", vm="db"), content="Port 2222 was taken; using 2223."),
    )
    run = svc.start(USER, "ssh on 2222 then start db", None)
    run = svc.approve(USER, run["id"], 1)

    assert run["status"] == "needs_approval" and run["plan_version"] == 2 and run["repairs"] == 1
    assert [s["status"] for s in run["plan"]] == ["failed", "skipped", "pending", "pending"]
    assert "2223" in run["plan"][2]["description"]

    run = svc.approve(USER, run["id"], 2)
    assert run["status"] == "completed"
    assert [tool for tool, _ in backend.executed] == ["add_port_rule", "start_vm"]


def test_second_failure_fails_the_run(backend):
    backend.failures = {"start_vm": "VBoxManage error", "start_vm:db": "VBoxManage error again"}
    svc = _service(
        backend,
        turn(call("start_vm", vm="db"), content="Queued."),
        turn(call("start_vm", vm="db"), content="Retrying."),
    )
    run = svc.start(USER, "start db", None)
    run = svc.approve(USER, run["id"], 1)
    run = svc.approve(USER, run["id"], 2)
    assert run["status"] == "failed" and "failed" in run["error"]


def test_executor_revalidates_against_current_state(backend):
    svc = _service(backend, turn(call("delete_vm", vm="db"), content="Queued."))
    run = svc.start(USER, "delete db", None)
    backend._world.vms["db"].status = "running"  # changed after planning
    svc.planner.llm.responses.append(say("db is running now; stop it first."))
    run = svc.approve(USER, run["id"], 1)
    assert run["plan"][0]["status"] == "failed"
    assert "running" in run["plan"][0]["result"]
    assert backend.executed == []


def test_cancel_before_approval(backend):
    svc = _service(backend, turn(call("delete_vm", vm="db"), content="Queued."))
    run = svc.start(USER, "delete db", None)
    run = svc.cancel(USER, run["id"])
    assert run["status"] == "cancelled" and run["plan"][0]["status"] == "skipped"
    assert backend.executed == []


def test_new_message_supersedes_pending_plan_and_sees_it_in_history(backend):
    svc = _service(
        backend,
        turn(call("delete_vm", vm="db"), content="Queued delete of db."),
        say("OK, I won't delete it."),
    )
    first = svc.start(USER, "delete db", None)
    second = svc.start(USER, "actually keep it", first["conversation_id"])
    assert svc.get(USER, first["id"])["status"] == "cancelled"
    assert second["status"] == "answered"
    history = svc.planner.llm.calls[1]
    assert any("Plan cancelled: 1. Delete 'db'" in m["content"] for m in history if m["role"] == "assistant")


# ─── routes ───────────────────────────────────────────────────────────────


def test_routes_end_to_end(backend):
    svc = _service(backend, turn(call("create_vm", name="a", ram=4096), content="Queued a."))
    app = FastAPI()
    app.include_router(agent_routes.router, prefix="/api/v1/agent")
    app.dependency_overrides[get_current_user] = lambda: UserClaims(id=USER, email="")
    app.dependency_overrides[agent_routes.get_agent_service] = lambda: svc
    client = TestClient(app)

    with patch("app.services.ai_service._log_ai_usage"), patch("app.services.ai_service._check_rate_limit"):
        run = client.post("/api/v1/agent/runs", json={"prompt": "make vm a"}).json()
    assert run["status"] == "needs_approval"
    assert run["risk"]["costly"] == 1 and run["resources"]["ram_mb"] == 4096

    assert client.post(f"/api/v1/agent/runs/{run['id']}/approve", json={"plan_version": 2}).status_code == 409
    done = client.post(f"/api/v1/agent/runs/{run['id']}/approve", json={"plan_version": 1}).json()
    assert done["status"] == "completed"
    assert [r["id"] for r in client.get("/api/v1/agent/runs").json()] == [run["id"]]
    assert client.get(f"/api/v1/agent/runs/{run['id']}").json()["trace"]
