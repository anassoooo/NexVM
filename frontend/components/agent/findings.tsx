import type { Finding } from "@/types";

const SEVERITY = {
  critical: { color: "#ff5252", label: "critical" },
  warning: { color: "var(--warning)", label: "warning" },
  info: { color: "var(--text-muted)", label: "info" },
} as const;

export default function Findings({ findings }: { findings: Finding[] }) {
  if (!findings.length) return null;
  return (
    <ul className="mt-3 space-y-2">
      {findings.map((f, i) => (
        <li key={`${f.vm}-${f.code}-${i}`} className="text-xs rounded-md px-3 py-2"
          style={{ background: "rgba(0,0,0,0.25)", borderLeft: `2px solid ${SEVERITY[f.severity].color}` }}>
          <div>
            <span className="font-semibold uppercase tracking-wider" style={{ color: SEVERITY[f.severity].color }}>
              {SEVERITY[f.severity].label}
            </span>
            <span style={{ color: "var(--text-muted)" }}> · {f.vm}</span>
          </div>
          <div style={{ color: "var(--text)" }}>{f.message}</div>
          {f.suggestion && <div style={{ color: "var(--text-muted)" }}>→ {f.suggestion}</div>}
        </li>
      ))}
    </ul>
  );
}
