import Link from "next/link";

/** The NexVM mark: a machine (solid square) inside a host (outline). Uses currentColor. */
export function LogoMark({ size = 24 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="2.25" y="2.25" width="19.5" height="19.5" rx="5" stroke="currentColor" strokeWidth="2.5" />
      <rect x="10" y="10" width="8" height="8" rx="2" fill="currentColor" />
    </svg>
  );
}

export default function Logo({ size = "md", collapsed = false }: { size?: "sm" | "md" | "lg"; collapsed?: boolean }) {
  const dim =
    size === "lg" ? { px: 32, text: "text-2xl" } :
    size === "md" ? { px: 24, text: "text-lg" } :
                   { px: 20, text: "text-base" };

  return (
    <Link href="/" aria-label={collapsed ? "NexVM home" : undefined} className="flex items-center gap-2.5" style={{ color: "var(--text)", textDecoration: "none" }}>
      <span style={{ color: "var(--accent)", display: "inline-flex" }}>
        <LogoMark size={dim.px} />
      </span>
      {!collapsed && <span className={`font-semibold tracking-tight ${dim.text}`}>NexVM</span>}
    </Link>
  );
}
