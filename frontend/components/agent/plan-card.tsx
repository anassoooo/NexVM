"use client";

import type { AgentRun, PlanStep, Risk, StepStatus } from "@/types";

const RISK_STYLE: Record<Risk, { label: string; color: string; bg: string }> = {
  low: { label: "low risk", color: "var(--text-muted)", bg: "color-mix(in srgb, var(--ink) 5%, transparent)" },
  costly: { label: "uses resources", color: "var(--info)", bg: "color-mix(in srgb, var(--info) 8%, transparent)" },
  destructive: { label: "destructive", color: "var(--warning)", bg: "color-mix(in srgb, var(--warning) 10%, transparent)" },
};

const STATUS_ICON: Record<StepStatus, { glyph: string; color: string }> = {
  pending: { glyph: "○", color: "var(--text-muted)" },
  running: { glyph: "◌", color: "var(--accent)" },
  done: { glyph: "●", color: "var(--success)" },
  failed: { glyph: "✕", color: "var(--warning)" },
  skipped: { glyph: "–", color: "var(--text-muted)" },
};

function StepRow({ step }: { step: PlanStep }) {
  const risk = RISK_STYLE[step.risk];
  const icon = STATUS_ICON[step.status];
  return (
    <li className="flex gap-3 py-2" style={{ borderTop: "1px solid var(--border)" }}>
      <span
        aria-label={step.status}
        className={step.status === "running" ? "animate-spin" : undefined}
        style={{ color: icon.color, width: 14, textAlign: "center", lineHeight: "20px", display: "inline-block" }}
      >
        {icon.glyph}
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span style={{ color: "var(--text)", opacity: step.status === "skipped" ? 0.5 : 1 }}>
            {step.index}. {step.description}
          </span>
          <span
            className="text-xs px-2 rounded-full"
            style={{ color: risk.color, background: risk.bg, lineHeight: "18px" }}
          >
            {risk.label}
          </span>
        </div>
        <div className="text-xs mt-0.5" style={{ color: step.status === "failed" ? "var(--warning)" : "var(--text-muted)" }}>
          {step.status === "pending" || step.status === "skipped"
            ? `→ ${step.effect}`
            : `${step.result}${step.duration_ms ? ` · ${(step.duration_ms / 1000).toFixed(1)} s` : ""}`}
        </div>
      </div>
    </li>
  );
}

export default function PlanCard({
  run,
  busy,
  onApprove,
  onCancel,
  readOnly = false,
}: {
  run: AgentRun;
  busy: boolean;
  onApprove: () => void;
  onCancel: () => void;
  readOnly?: boolean;
}) {
  if (!run.plan.length) return null;
  const waiting = run.status === "needs_approval" && !readOnly;
  const { resources: r } = run;
  const destructive = run.plan.some((s) => s.status === "pending" && s.risk === "destructive");

  return (
    <div className="mt-3 rounded-lg" style={{ border: "1px solid var(--border)", background: "var(--surface-inset)" }}>
      <div className="flex items-center justify-between px-3 py-2">
        <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--accent)" }}>
          Plan{run.plan_version > 1 ? ` · revision ${run.plan_version}` : ""}
        </span>
        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
          {run.status === "running" ? "running…" : run.status.replace("_", " ")}
        </span>
      </div>
      <ul className="px-3">
        {run.plan.map((s) => (
          <StepRow key={s.index} step={s} />
        ))}
      </ul>
      {waiting && (
        <div className="px-3 py-3 flex flex-wrap items-center gap-3" style={{ borderTop: "1px solid var(--border)" }}>
          {r.new_vms > 0 && (
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              Adds {r.new_vms} VM{r.new_vms > 1 ? "s" : ""}
              {r.ram_mb ? ` · ${r.ram_mb / 1024} GB RAM · ${r.cpu} vCPU · ${Math.round(r.disk_mb / 1024)} GB disk` : ""}
            </span>
          )}
          <div className="flex gap-2 ml-auto">
            <button type="button" onClick={onCancel} disabled={busy} className="glass text-sm font-semibold"
              style={{ padding: "6px 16px", borderRadius: 9999, color: "var(--text)", cursor: busy ? "not-allowed" : "pointer" }}>
              Cancel
            </button>
            <button type="button" onClick={onApprove} disabled={busy} className="btn-primary"
              style={{ padding: "6px 18px", ...(destructive ? { background: "var(--warning)" } : {}) }}>
              {destructive ? "Approve (destructive)" : "Approve plan"}
            </button>
          </div>
        </div>
      )}
      {run.error && run.status !== "needs_approval" && (
        <div className="px-3 pb-3 text-xs" style={{ color: "var(--warning)" }}>{run.error}</div>
      )}
    </div>
  );
}
