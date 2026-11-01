"use client";

import { useEffect, useRef, useState } from "react";
import PlanCard from "@/components/agent/plan-card";
import { Button } from "@/components/ui";
import type { AgentRun, PlanStep } from "@/types";

// A run recorded from the live app (docs/demo); approving it here replays what happened on the host.
const PROMPT = "Create a VM called demo-web with 1 GB RAM and 1 vCPU, then start it";
const STEPS: PlanStep[] = [
  {
    index: 1, tool: "create_vm", args: {}, risk: "costly",
    description: "Create VM 'demo-web' (Ubuntu 22.04, 1 vCPU, 1024 MB RAM, 20 GB disk)",
    effect: "'demo-web' will exist (stopped)", status: "pending", result: "created 'demo-web'", duration_ms: 1700,
  },
  {
    index: 2, tool: "start_vm", args: {}, risk: "low",
    description: "Start 'demo-web'",
    effect: "'demo-web' will be running", status: "pending", result: "'demo-web' is starting", duration_ms: 6000,
  },
];
const RUN: AgentRun = {
  id: "demo", conversation_id: "demo", prompt: PROMPT, status: "needs_approval", answer: null,
  plan: STEPS, plan_version: 1, findings: [], trace: [], model: "openai/gpt-oss-20b",
  total_tokens: 5235, latency_ms: 2900, repairs: 0, error: null, created_at: "", risk: { costly: 1, low: 1 },
  resources: { new_vms: 1, ram_mb: 1024, cpu: 1, disk_mb: 20480 },
};

type Phase = "waiting" | "running" | "done" | "cancelled";

export default function PlanPreview() {
  const [run, setRun] = useState<AgentRun>(RUN);
  const [phase, setPhase] = useState<Phase>("waiting");
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => () => timers.current.forEach(clearTimeout), []);

  function setSteps(statuses: PlanStep["status"][], status: AgentRun["status"]) {
    setRun({ ...RUN, status, plan: STEPS.map((s, i) => ({ ...s, status: statuses[i] })) });
  }

  function approve() {
    setPhase("running");
    // The real steps took 1.7 s and 6.0 s; the replay compresses them.
    const frames: [number, PlanStep["status"][], AgentRun["status"]][] = [
      [0, ["running", "pending"], "running"],
      [700, ["done", "running"], "running"],
      [1600, ["done", "done"], "completed"],
    ];
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    for (const [at, statuses, status] of reduce ? frames.slice(-1) : frames) {
      timers.current.push(setTimeout(() => setSteps(statuses, status), reduce ? 0 : at));
    }
    timers.current.push(setTimeout(() => setPhase("done"), reduce ? 0 : 1600));
  }

  function cancel() {
    setRun({ ...RUN, status: "cancelled", plan: STEPS.map((s) => ({ ...s, status: "skipped" })) });
    setPhase("cancelled");
  }

  function reset() {
    timers.current.forEach(clearTimeout);
    timers.current = [];
    setRun(RUN);
    setPhase("waiting");
  }

  return (
    <div className="card p-4 sm:p-5" style={{ boxShadow: "var(--shadow-lg)" }}>
      <div className="flex justify-end">
        <div className="text-sm font-medium max-w-[85%]"
          style={{ background: "var(--accent)", color: "var(--on-accent)", borderRadius: "12px 12px 4px 12px", padding: "10px 14px" }}>
          {PROMPT}
        </div>
      </div>
      <PlanCard run={run} busy={phase === "running"} onApprove={approve} onCancel={cancel} />
      <div className="mt-3 flex items-center justify-between gap-3 text-xs" style={{ color: "var(--text-muted)" }} aria-live="polite">
        <span>
          {phase === "waiting" && "Planned in 2.9 s with 5,235 tokens. Nothing has run yet."}
          {phase === "running" && "Running the approved steps…"}
          {phase === "done" && "Both steps ran. The trace records every model and tool call."}
          {phase === "cancelled" && "Cancelled. Nothing ran on the host."}
        </span>
        {(phase === "done" || phase === "cancelled") && (
          <Button variant="ghost" size="sm" onClick={reset}>Replay</Button>
        )}
      </div>
    </div>
  );
}
