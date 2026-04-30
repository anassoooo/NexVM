"use client";

import { useEffect, useState } from "react";
import { Log, AIUsage } from "@/types";
import { api } from "@/lib/api";

type Tab = "activity" | "ai-usage";

const ACTION_COLOR: Record<string, string> = {
  create_vm:        "var(--accent)",
  start_vm:         "var(--success)",
  stop_vm:          "var(--text-muted)",
  delete_vm:        "var(--warning)",
  login:            "#64b4ff",
  ai_command:       "#b47fff",
  modify_vm:        "var(--accent)",
  pause_vm:         "#64b4ff",
  resume_vm:        "var(--success)",
  save_state:       "#64b4ff",
  add_port_rule:    "var(--accent)",
  remove_port_rule: "var(--warning)",
  take_snapshot:    "var(--accent)",
  restore_snapshot: "#b47fff",
  delete_snapshot:  "var(--warning)",
};

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n) + "…" : s;
}

export default function LogsClient() {
  const [tab, setTab]           = useState<Tab>("activity");
  const [logs, setLogs]         = useState<Log[]>([]);
  const [aiUsage, setAiUsage]   = useState<AIUsage[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      setLoading(true);
      setError(null);
      try {
        const [logsData, aiData] = await Promise.all([
          api.get<Log[]>("/api/v1/logs"),
          api.get<AIUsage[]>("/api/v1/logs/ai-usage"),
        ]);
        setLogs(logsData);
        setAiUsage(aiData);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load logs");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const tabStyle = (t: Tab) => ({
    padding: "6px 18px",
    borderRadius: 6,
    fontSize: 13,
    fontWeight: 500,
    cursor: "pointer",
    border: "1px solid",
    borderColor: tab === t ? "var(--accent)" : "var(--border)",
    background: tab === t ? "rgba(0,230,118,0.08)" : "transparent",
    color: tab === t ? "var(--accent)" : "var(--text-muted)",
    transition: "all .15s",
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>
          Activity Logs
        </h1>
        <div className="flex gap-2">
          <button style={tabStyle("activity")} onClick={() => setTab("activity")}>
            Activity
            {logs.length > 0 && (
              <span style={{ marginLeft: 6, opacity: 0.6 }}>{logs.length}</span>
            )}
          </button>
          <button style={tabStyle("ai-usage")} onClick={() => setTab("ai-usage")}>
            AI Usage
            {aiUsage.length > 0 && (
              <span style={{ marginLeft: 6, opacity: 0.6 }}>{aiUsage.length}</span>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div
          className="mb-4 p-3 rounded text-sm"
          style={{ background: "rgba(255,109,0,0.1)", color: "var(--warning)", border: "1px solid rgba(255,109,0,0.2)" }}
        >
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex flex-col gap-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="glass animate-pulse h-12" style={{ opacity: 0.4 }} />
          ))}
        </div>
      ) : tab === "activity" ? (
        <ActivityTable logs={logs} />
      ) : (
        <AIUsageTable rows={aiUsage} />
      )}
    </div>
  );
}

function ActivityTable({ logs }: { logs: Log[] }) {
  if (logs.length === 0) {
    return <Empty text="No activity yet" />;
  }
  return (
    <div className="glass" style={{ overflow: "hidden" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ borderBottom: "1px solid var(--border)" }}>
            {["Action", "Target", "Status", "Message", "Date"].map((h) => (
              <th key={h} style={{ padding: "10px 14px", textAlign: "left", color: "var(--text-muted)", fontWeight: 500 }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {logs.map((log) => (
            <tr
              key={log.id}
              style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}
            >
              <td style={{ padding: "9px 14px" }}>
                <span
                  style={{
                    color: ACTION_COLOR[log.action] ?? "var(--text)",
                    fontFamily: "monospace",
                    fontSize: 12,
                  }}
                >
                  {log.action}
                </span>
              </td>
              <td style={{ padding: "9px 14px", color: "var(--text)", maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {truncate(log.target, 24)}
              </td>
              <td style={{ padding: "9px 14px" }}>
                <span
                  style={{
                    fontSize: 11,
                    padding: "2px 8px",
                    borderRadius: 4,
                    background: log.status === "success" ? "rgba(0,230,118,0.12)" : "rgba(255,109,0,0.12)",
                    color: log.status === "success" ? "var(--success)" : "var(--warning)",
                  }}
                >
                  {log.status}
                </span>
              </td>
              <td style={{ padding: "9px 14px", color: "var(--text-muted)", maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {truncate(log.message, 60)}
              </td>
              <td style={{ padding: "9px 14px", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
                {fmtDate(log.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AIUsageTable({ rows }: { rows: AIUsage[] }) {
  if (rows.length === 0) {
    return <Empty text="No AI commands yet" />;
  }
  return (
    <div className="flex flex-col gap-3">
      {rows.map((row) => (
        <div key={row.id} className="glass" style={{ padding: "14px 18px" }}>
          <div className="flex items-start justify-between gap-4 mb-2">
            <p style={{ color: "var(--text)", fontSize: 14, flex: 1 }}>
              {truncate(row.prompt, 120)}
            </p>
            <span style={{ color: "var(--text-muted)", fontSize: 12, whiteSpace: "nowrap" }}>
              {fmtDate(row.created_at)}
            </span>
          </div>
          <p style={{ color: "var(--text-muted)", fontSize: 13, marginBottom: 6 }}>
            {truncate(row.response, 160)}
          </p>
          <span style={{ fontSize: 11, color: "#b47fff" }}>
            {row.tokens} tokens
          </span>
        </div>
      ))}
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return (
    <p className="text-center py-16" style={{ color: "var(--text-muted)" }}>
      {text}
    </p>
  );
}
