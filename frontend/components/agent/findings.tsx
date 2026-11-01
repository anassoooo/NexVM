import type { Finding } from "@/types";
import { Badge, type Tone } from "@/components/ui";

const SEVERITY: Record<Finding["severity"], { tone: Tone; color: string }> = {
  critical: { tone: "danger", color: "var(--danger)" },
  warning: { tone: "warning", color: "var(--warning)" },
  info: { tone: "neutral", color: "var(--border-strong)" },
};

export default function Findings({ findings }: { findings: Finding[] }) {
  if (!findings.length) return null;
  return (
    <ul className="mt-3 space-y-2">
      {findings.map((f, i) => (
        <li key={`${f.vm}-${f.code}-${i}`} className="text-sm rounded-md px-3 py-2"
          style={{ background: "var(--surface-inset)", borderLeft: `3px solid ${SEVERITY[f.severity].color}` }}>
          <div className="flex items-center gap-2 mb-0.5">
            <Badge tone={SEVERITY[f.severity].tone}>{f.severity}</Badge>
            <code className="text-xs" style={{ color: "var(--text-muted)" }}>{f.vm}</code>
          </div>
          <div style={{ color: "var(--text)" }}>{f.message}</div>
          {f.suggestion && <div className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>Suggestion: {f.suggestion}</div>}
        </li>
      ))}
    </ul>
  );
}
