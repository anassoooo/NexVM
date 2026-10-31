"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import Findings from "@/components/agent/findings";
import PlanCard from "@/components/agent/plan-card";
import TraceTimeline from "@/components/agent/trace-timeline";
import { api } from "@/lib/api";
import type { AgentRun } from "@/types";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="card px-4 py-3">
      <div className="text-xs" style={{ color: "var(--text-muted)" }}>{label}</div>
      <div className="text-lg font-semibold tabular-nums" style={{ color: "var(--text)" }}>{value}</div>
    </div>
  );
}

export default function RunDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [run, setRun] = useState<AgentRun | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const load = () =>
      api.get<AgentRun>(`/api/v1/agent/runs/${id}`)
        .then((r) => {
          setRun(r);
          if (r.status === "running") timer = setTimeout(load, 1000);
        })
        .catch((e: Error) => setError(e.message));
    load();
    return () => clearTimeout(timer);
  }, [id]);

  if (error) return <p className="px-6 py-6 text-sm" style={{ color: "var(--warning)" }}>{error}</p>;
  if (!run) return <p className="px-6 py-6 text-sm" style={{ color: "var(--text-muted)" }}>Loading…</p>;

  const llmCalls = run.trace.filter((s) => s.kind === "llm").length;
  const toolCalls = run.trace.filter((s) => s.kind === "tool").length;
  const rejected = run.trace.filter((s) => s.kind === "tool" && !s.ok).length;

  return (
    <div className="max-w-4xl mx-auto w-full px-6 py-6 space-y-5">
      <Link href="/ai/runs" className="text-sm nav-link">All runs</Link>

      <div className="card px-5 py-4">
        <div className="text-xs mb-1" style={{ color: "var(--text-muted)" }}>Request</div>
        <div className="text-base font-semibold" style={{ color: "var(--text)" }}>{run.prompt}</div>
        <div className="text-xs mt-3 mb-1" style={{ color: "var(--text-muted)" }}>Reply</div>
        <div className="text-sm whitespace-pre-wrap" style={{ color: "var(--text)" }}>{run.answer}</div>
        <Findings findings={run.findings} />
        <PlanCard run={run} busy readOnly onApprove={() => {}} onCancel={() => {}} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Planning" value={`${(run.latency_ms / 1000).toFixed(1)} s`} />
        <Stat label="Tokens" value={run.total_tokens.toLocaleString()} />
        <Stat label="Model calls" value={String(llmCalls)} />
        <Stat label="Tool calls" value={`${toolCalls}${rejected ? ` (${rejected} fixed)` : ""}`} />
      </div>

      <div className="card px-5 py-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-semibold" style={{ color: "var(--text)" }}>Trace</span>
          <code className="text-xs" style={{ color: "var(--text-muted)" }}>{run.model}</code>
        </div>
        <TraceTimeline spans={run.trace} />
      </div>
    </div>
  );
}
