"use client";

import type { AgentRun, PlanStep, Risk, StepStatus } from "@/types";
import { Badge, Button, type Tone } from "@/components/ui";

const RISK: Record<Risk, { label: string; tone: Tone }> = {
  low: { label: "low risk", tone: "neutral" },
  costly: { label: "uses resources", tone: "info" },
  destructive: { label: "destructive", tone: "warning" },
};

const STATUS_ICON: Record<StepStatus, { glyph: string; color: string }> = {
  pending: { glyph: "○", color: "var(--text-muted)" },
  running: { glyph: "◌", color: "var(--accent)" },
  done: { glyph: "●", color: "var(--success)" },
  failed: { glyph: "✕", color: "var(--warning)" },
  skipped: { glyph: "–", color: "var(--text-muted)" },
};

const RUN_STATUS: Partial<Record<AgentRun["status"], string>> = {
  needs_approval: "Waiting for approval",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
};

function StepRow({ step }: { step: PlanStep }) {
  const risk = RISK[step.risk];
  const icon = STATUS_ICON[step.status];
  return (
    <li className="flex gap-3 py-2.5" style={{ borderTop: "1px solid var(--border)" }}>
      <span
        aria-label={step.status}
        className={step.status === "running" ? "animate-spin" : undefined}
        style={{ color: icon.color, width: 14, textAlign: "center", lineHeight: "20px", display: "inline-block" }}
      >
        {icon.glyph}
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span className="text-sm" style={{ color: "var(--text)", opacity: step.status === "skipped" ? 0.5 : 1 }}>
            {step.index}. {step.description}
          </span>
          <Badge tone={risk.tone}>{risk.label}</Badge>
        </div>
        <div className="text-xs mt-0.5" style={{ color: step.status === "failed" ? "var(--warning)" : "var(--text-muted)" }}>
          <code>{step.tool}</code>{" "}
          {step.status === "pending" || step.status === "skipped"
            ? `then ${step.effect}`
            : `${step.result}${step.duration_ms ? ` (${(step.duration_ms / 1000).toFixed(1)} s)` : ""}`}
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
        <span className="text-sm font-semibold" style={{ color: "var(--text)" }}>
          Plan{run.plan_version > 1 ? `, revision ${run.plan_version}` : ""}
        </span>
        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
          {RUN_STATUS[run.status] ?? run.status}
        </span>
      </div>
      <ol className="px-3">
        {run.plan.map((s) => (
          <StepRow key={s.index} step={s} />
        ))}
      </ol>
      {waiting && (
        <div className="px-3 py-3 flex flex-wrap items-center gap-3" style={{ borderTop: "1px solid var(--border)" }}>
          {r.new_vms > 0 && (
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              Adds {r.new_vms} VM{r.new_vms > 1 ? "s" : ""}
              {r.ram_mb ? `: ${r.ram_mb / 1024} GB RAM, ${r.cpu} vCPU, ${Math.round(r.disk_mb / 1024)} GB disk` : ""}
            </span>
          )}
          <div className="flex gap-2 ml-auto">
            <Button variant="secondary" onClick={onCancel} disabled={busy}>Cancel</Button>
            <Button variant={destructive ? "danger" : "primary"} onClick={onApprove} disabled={busy}>
              {destructive ? "Approve destructive plan" : "Approve plan"}
            </Button>
          </div>
        </div>
      )}
      {run.error && run.status !== "needs_approval" && (
        <div className="px-3 pb-3 text-xs" style={{ color: "var(--warning)" }}>{run.error}</div>
      )}
    </div>
  );
}
