"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AgentRunSummary, RunStatus } from "@/types";

const STATUS_COLOR: Record<RunStatus, string> = {
  answered: "var(--text-muted)",
  needs_approval: "#40c4ff",
  running: "var(--accent)",
  completed: "var(--success)",
  failed: "var(--warning)",
  cancelled: "var(--text-muted)",
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
          <h1 className="text-lg font-bold" style={{ color: "var(--text)" }}>Autopilot runs</h1>
          {runs && totals && runs.length > 0 && (
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              {runs.length} runs · {totals.tokens.toLocaleString()} tokens · avg {(totals.ms / runs.length / 1000).toFixed(1)} s planning
            </p>
          )}
        </div>
        <Link href="/ai" className="text-xs nav-link">← Back to Autopilot</Link>
      </div>

      {error && <p className="text-sm" style={{ color: "var(--warning)" }}>{error}</p>}
      {runs && runs.length === 0 && <p className="text-sm" style={{ color: "var(--text-muted)" }}>No runs yet.</p>}

      <ul className="space-y-2">
        {runs?.map((r) => (
          <li key={r.id}>
            <Link href={`/ai/runs/${r.id}`} className="glass block px-4 py-3" style={{ textDecoration: "none" }}>
              <div className="flex items-center justify-between gap-3">
                <span className="truncate text-sm" style={{ color: "var(--text)" }}>{r.prompt}</span>
                <span className="text-xs whitespace-nowrap" style={{ color: STATUS_COLOR[r.status] }}>{r.status.replace("_", " ")}</span>
              </div>
              <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                {new Date(r.created_at).toLocaleString()} · {(r.latency_ms / 1000).toFixed(1)} s · {r.total_tokens} tokens · {r.model}
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
