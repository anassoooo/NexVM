"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AgentRunSummary, RunStatus } from "@/types";
import { Badge, type Tone } from "@/components/ui";

const STATUS: Record<RunStatus, { label: string; tone: Tone }> = {
  answered: { label: "answered", tone: "neutral" },
  needs_approval: { label: "waiting for approval", tone: "info" },
  running: { label: "running", tone: "accent" },
  completed: { label: "completed", tone: "accent" },
  failed: { label: "failed", tone: "warning" },
  cancelled: { label: "cancelled", tone: "neutral" },
};

export default function RunsPage() {
  const [runs, setRuns] = useState<AgentRunSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<AgentRunSummary[]>("/api/v1/agent/runs?limit=50").then(setRuns).catch((e: Error) => setError(e.message));
  }, []);

  const totals = runs?.reduce((a, r) => ({ tokens: a.tokens + r.total_tokens, ms: a.ms + r.latency_ms }), { tokens: 0, ms: 0 });

  return (
    <div className="max-w-4xl mx-auto w-full px-6 py-6">
      <div className="flex items-end justify-between mb-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight" style={{ color: "var(--text)" }}>Run history</h1>
          {runs && totals && runs.length > 0 && (
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              {runs.length} runs, {totals.tokens.toLocaleString()} tokens in total, {(totals.ms / runs.length / 1000).toFixed(1)} s average planning time
            </p>
          )}
        </div>
        <Link href="/ai" className="text-sm nav-link">Back to Autopilot</Link>
      </div>

      {error && <p className="text-sm" style={{ color: "var(--warning)" }}>{error}</p>}
      {runs && runs.length === 0 && <p className="text-sm" style={{ color: "var(--text-muted)" }}>No runs yet. Ask Autopilot for a change and it appears here with its full trace.</p>}

      <ul className="space-y-2">
        {runs?.map((r) => (
          <li key={r.id}>
            <Link href={`/ai/runs/${r.id}`} className="card block px-4 py-3" style={{ textDecoration: "none" }}>
              <div className="flex items-center justify-between gap-3">
                <span className="truncate text-sm" style={{ color: "var(--text)" }}>{r.prompt}</span>
                <Badge tone={STATUS[r.status].tone}>{STATUS[r.status].label}</Badge>
              </div>
              <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                {new Date(r.created_at).toLocaleString()}, planned in {(r.latency_ms / 1000).toFixed(1)} s with {r.total_tokens.toLocaleString()} tokens by <code>{r.model}</code>
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
