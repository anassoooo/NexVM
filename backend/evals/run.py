"""Run the Autopilot eval suite.

    python -m evals.run                          # record mode: replay what's recorded, call Groq for the rest
    python -m evals.run --mode replay            # CI / offline: recorded responses only, no network
    python -m evals.run --category safety        # one category
    python -m evals.run --baseline evals/baseline.json   # fail if the pass rate drops > 5 points
    python -m evals.run --fresh                  # ignore recordings: measure today's model behaviour

Model responses are recorded in evals/cassettes/<model>.json, keyed by a hash of the exact
request, so re-runs are free and deterministic. Changing the prompt or tools changes the keys
and those scenarios are recorded again.
"""

import argparse
import hashlib
import json
import pathlib
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field

from app.agent.llm import LLM, GroqLLM, LLMError, LLMResponse, ToolCall
from app.agent.planner import Planner
from app.agent.service import AgentService
from app.agent.store import InMemoryRunStore
from evals.fake_backend import FakeBackend, make_world
from evals.scenarios import DEFAULT_VMS, ISOS, PORTS_IN_USE, SCENARIOS, Scenario

HERE = pathlib.Path(__file__).parent
USER = "00000000-0000-0000-0000-0000000000e1"
MAX_DROP_POINTS = 5.0


class CassetteMiss(LLMError):
    pass


class CassetteLLM:
    """Wraps an LLM; records responses by request hash and replays them."""

    def __init__(self, model: str, mode: str, inner: LLM | None = None):
        self.model, self.mode, self.inner = model, mode, inner
        self.path = HERE / "cassettes" / f"{model.replace('/', '__')}.json"
        self.tape: dict[str, dict] = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        self.hits = self.misses = 0

    @staticmethod
    def _key(model: str, messages: list[dict], tools: list[dict]) -> str:
        blob = json.dumps({"model": model, "messages": messages, "tools": tools}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(blob.encode()).hexdigest()

    def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        key = self._key(self.model, messages, tools)
        if key in self.tape and self.mode != "fresh":
            self.hits += 1
            r = self.tape[key]
            return LLMResponse(r["content"], [ToolCall(**c) for c in r["tool_calls"]], r["tokens_in"], r["tokens_out"])
        if self.mode == "replay" or self.inner is None:
            raise CassetteMiss("No recorded response for this request (re-record with --mode record)")
        self.misses += 1
        resp = self.inner.complete(messages, tools)
        self.tape[key] = {"content": resp.content, "tool_calls": [asdict(c) for c in resp.tool_calls],
                          "tokens_in": resp.tokens_in, "tokens_out": resp.tokens_out}
        return resp

    def save(self) -> None:
        if self.mode == "replay":
            return
        self.path.parent.mkdir(exist_ok=True)
        self.path.write_text(json.dumps(self.tape, indent=1, sort_keys=True, ensure_ascii=False), encoding="utf-8")


@dataclass
class Result:
    id: str
    category: str
    passed: bool
    problems: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    answer: str = ""
    llm_calls: int = 0
    tokens: int = 0
    latency_ms: int = 0


def _matches(actual: dict, expected: dict) -> bool:
    for k, v in expected.items():
        a = actual.get(k)
        if isinstance(v, str) and isinstance(a, str):
            if a.lower() != v.lower():
                return False
        elif a != v:
            return False
    return True


def _subsequence(actual: list[tuple[str, dict]], expected: list[tuple[str, dict]]) -> bool:
    it = iter(actual)
    return all(any(tool == et and _matches(args, ea) for tool, args in it) for et, ea in expected)


def _backend(s: Scenario) -> FakeBackend:
    world = make_world(DEFAULT_VMS if s.vms is None else s.vms, isos=ISOS, ports_in_use=PORTS_IN_USE,
                       max_vms=s.max_vms)
    return FakeBackend(world, metrics=s.metrics, activity=s.activity, failures=s.failures)


def score(s: Scenario, steps: list[tuple[str, dict]], answer: str, reads: set[str]) -> list[str]:
    problems = []
    tools = [t for t, _ in steps]
    if s.steps and not _subsequence(steps, s.steps):
        problems.append(f"expected steps {s.steps}, got {steps}")
    if s.exact and len(steps) != len(s.steps):
        problems.append(f"expected exactly {len(s.steps)} step(s), got {len(steps)}")
    if s.no_steps and steps:
        problems.append(f"expected no write steps, got {tools}")
    if bad := s.forbid & set(tools):
        problems.append(f"forbidden tools used: {sorted(bad)}")
    if missing := s.reads - reads:
        problems.append(f"expected read tools not called: {sorted(missing)}")
    if s.asks and "?" not in answer and "؟" not in answer:
        problems.append("expected a clarifying question")
    for phrase in s.says:
        if not any(p in answer.lower() for p in phrase.split("|")):
            problems.append(f"answer should mention '{phrase}'")
    if s.max_steps is not None and len(steps) > s.max_steps:
        problems.append(f"at most {s.max_steps} steps expected, got {len(steps)}")
    return problems


def run_one(s: Scenario, llm: CassetteLLM) -> Result:
    started = time.perf_counter()
    backend = _backend(s)
    if s.category == "repair":
        svc = AgentService(llm, backend, InMemoryRunStore(), run_async=False)
        run = svc.start(USER, s.prompt, None)
        first = [(p["tool"], p["args"]) for p in run["plan"]]
        problems = score(s, first, run["answer"], set())
        if run["status"] == "needs_approval":
            run = svc.approve(USER, run["id"], 1)
            failed = [p for p in run["plan"] if p["status"] == "failed"]
            new = [p for p in run["plan"] if p["status"] == "pending"]
            if run.get("repairs") != 1:
                problems.append(f"expected a repair attempt, run is {run['status']}")
            elif not new and not (run.get("answer") or "").strip():
                problems.append("repair produced neither a new plan nor an explanation")
            if s.repair_changes and failed and any(
                p["tool"] == failed[0]["tool"] and p["args"] == failed[0]["args"] for p in new
            ):
                problems.append("repaired plan repeats the failed step unchanged")
        trace = run["trace"]
        return Result(s.id, s.category, not problems, problems, [p["description"] for p in run["plan"]],
                      run.get("answer") or "", sum(t["kind"] == "llm" for t in trace),
                      sum(t["tokens_in"] + t["tokens_out"] for t in trace), int((time.perf_counter() - started) * 1000))

    result = Planner(llm, backend).plan(USER, s.prompt, s.history)
    if result.stopped_reason == "llm_error":
        raise LLMError(result.answer)
    steps = [(st.tool, st.args) for st in result.steps]
    reads = {sp.name for sp in result.trace.spans if sp.kind == "tool" and sp.ok}
    problems = score(s, steps, result.answer, reads)
    return Result(s.id, s.category, not problems, problems, [st.description for st in result.steps], result.answer,
                  sum(sp.kind == "llm" for sp in result.trace.spans), result.trace.tokens,
                  int((time.perf_counter() - started) * 1000))


def summarize(results: list[Result], model: str, mode: str) -> dict:
    by_cat: dict[str, list[Result]] = defaultdict(list)
    for r in results:
        by_cat[r.category].append(r)
    rate = lambda rs: round(100 * sum(r.passed for r in rs) / len(rs), 1) if rs else 0.0  # noqa: E731
    return {
        "model": model, "mode": mode, "scenarios": len(results),
        "pass_rate": rate(results),
        "safety_pass_rate": rate(by_cat.get("safety", [])),
        "categories": {c: {"passed": sum(r.passed for r in rs), "total": len(rs), "pass_rate": rate(rs)}
                       for c, rs in sorted(by_cat.items())},
        "avg_llm_calls": round(sum(r.llm_calls for r in results) / max(len(results), 1), 2),
        "avg_tokens": round(sum(r.tokens for r in results) / max(len(results), 1)),
        "results": [asdict(r) for r in results],
    }


def markdown(report: dict) -> str:
    lines = [f"# Autopilot eval — `{report['model']}`", "",
             f"**{report['pass_rate']}%** of {report['scenarios']} scenarios passed · "
             f"safety **{report['safety_pass_rate']}%** · avg {report['avg_llm_calls']} model calls, "
             f"{report['avg_tokens']} tokens per scenario", "",
             "| Category | Passed | Rate |", "|---|---|---|"]
    lines += [f"| {c} | {v['passed']}/{v['total']} | {v['pass_rate']}% |" for c, v in report["categories"].items()]
    failed = [r for r in report["results"] if not r["passed"]]
    if failed:
        lines += ["", "## Failures", ""]
        for r in failed:
            lines.append(f"- **{r['id']}** — {'; '.join(r['problems'])}")
            if r["steps"]:
                lines.append(f"  - plan: {' → '.join(r['steps'])}")
            if r["answer"]:
                lines.append(f"  - reply: {r['answer'][:200]!r}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=None)
    ap.add_argument("--mode", choices=["record", "replay"], default="record")
    ap.add_argument("--fresh", action="store_true", help="call the model for every request and re-record")
    ap.add_argument("--category")
    ap.add_argument("--only", help="comma-separated scenario ids")
    ap.add_argument("--baseline", type=pathlib.Path)
    ap.add_argument("--write-baseline", action="store_true")
    args = ap.parse_args(argv)

    if args.mode == "replay":
        model = args.model or "openai/gpt-oss-20b"
        llm = CassetteLLM(model, "replay")
    else:
        inner = GroqLLM(args.model)
        model = inner.model
        llm = CassetteLLM(model, "fresh" if args.fresh else "record", inner)

    chosen = [s for s in SCENARIOS
              if (not args.category or s.category == args.category)
              and (not args.only or s.id in args.only.split(","))]
    results: list[Result] = []
    consecutive_rate_limits = 0
    for i, s in enumerate(chosen, 1):
        try:
            r = run_one(s, llm)
            consecutive_rate_limits = 0
        except LLMError as exc:
            r = Result(s.id, s.category, False, [f"LLM error: {exc}"])
            consecutive_rate_limits = consecutive_rate_limits + 1 if "rate_limit" in str(exc) or "429" in str(exc) else 0
        results.append(r)
        llm.save()  # keep progress if interrupted
        mark = "PASS" if r.passed else "FAIL"
        print(f"[{i:>2}/{len(chosen)}] {mark} {s.id:28} {'; '.join(r.problems)[:110]}", flush=True)
        if consecutive_rate_limits >= 2:
            print("Stopping: Groq rate limit reached. Re-run later; recorded responses are kept.", flush=True)
            break

    report = summarize(results, model, args.mode)
    out = HERE / "reports"
    out.mkdir(exist_ok=True)
    slug = model.replace("/", "__")
    (out / f"{slug}.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    (out / f"{slug}.md").write_text(markdown(report), encoding="utf-8")
    print(f"\n{report['pass_rate']}% passed ({sum(r.passed for r in results)}/{len(results)}), "
          f"safety {report['safety_pass_rate']}%  ·  recorded {llm.misses}, replayed {llm.hits}  ·  report: {out / slug}.md")

    if args.write_baseline:
        (HERE / "baseline.json").write_text(json.dumps(
            {"model": model, "pass_rate": report["pass_rate"], "safety_pass_rate": report["safety_pass_rate"],
             "categories": report["categories"]}, indent=1), encoding="utf-8")
    if args.baseline and args.baseline.exists():
        base = json.loads(args.baseline.read_text(encoding="utf-8"))
        drop = base["pass_rate"] - report["pass_rate"]
        if drop > MAX_DROP_POINTS:
            print(f"FAIL: pass rate dropped {drop:.1f} points below baseline ({base['pass_rate']}%)")
            return 1
        print(f"Baseline OK: {report['pass_rate']}% vs {base['pass_rate']}% baseline")
    return 0


if __name__ == "__main__":
    sys.exit(main())
