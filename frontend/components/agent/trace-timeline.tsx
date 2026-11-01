import type { TraceSpan } from "@/types";

const KIND = {
  llm: { color: "var(--violet)", label: "model" },
  tool: { color: "var(--info)", label: "tool" },
  step: { color: "var(--accent)", label: "step" },
} as const;

function ms(v: number) {
  return v >= 1000 ? `${(v / 1000).toFixed(1)} s` : `${v} ms`;
}

/** Waterfall of model calls, tool calls and executed steps (§XIV.5). */
export default function TraceTimeline({ spans }: { spans: TraceSpan[] }) {
  if (!spans.length) return <p className="text-sm" style={{ color: "var(--text-muted)" }}>No trace recorded.</p>;
  const end = Math.max(...spans.map((s) => s.start_ms + s.duration_ms), 1);

  return (
    <div>
      <div className="flex gap-4 mb-3 text-xs" style={{ color: "var(--text-muted)" }}>
        {Object.entries(KIND).map(([k, v]) => (
          <span key={k} className="flex items-center gap-1.5">
            <span style={{ width: 10, height: 10, borderRadius: 2, background: v.color, display: "inline-block" }} />
            {v.label}
          </span>
        ))}
      </div>
      <ol className="space-y-1.5">
        {spans.map((s, i) => {
          const left = (s.start_ms / end) * 100;
          const width = Math.max((s.duration_ms / end) * 100, 0.6);
          const color = s.ok ? KIND[s.kind].color : "var(--warning)";
          const tokens = s.tokens_in + s.tokens_out;
          return (
            <li key={i} className="grid items-center gap-3 text-xs" style={{ gridTemplateColumns: "minmax(110px, 180px) 1fr 120px" }}>
              <span className="truncate" title={s.detail} style={{ color: s.ok ? "var(--text)" : "var(--warning)" }}>
                {s.kind === "llm" ? "model call" : s.name}
              </span>
              <span className="relative h-3 rounded" style={{ background: "color-mix(in srgb, var(--ink) 4%, transparent)" }}>
                <span className="absolute top-0 h-3 rounded"
                  style={{ left: `${left}%`, width: `${width}%`, background: color, opacity: 0.85 }} />
              </span>
              <span className="text-right tabular-nums" style={{ color: "var(--text-muted)" }}>
                {ms(s.duration_ms)}
                {tokens ? ` · ${tokens} tok` : ""}
              </span>
              {s.detail && (
                <span className="col-span-3 -mt-1 truncate pl-1" style={{ color: "var(--text-muted)", opacity: 0.8 }}>
                  {s.detail}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
