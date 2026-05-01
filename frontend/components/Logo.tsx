import Image from "next/image";
import Link from "next/link";

export default function Logo({ size = "md", collapsed = false }: { size?: "sm" | "md" | "lg"; collapsed?: boolean }) {
  const dim =
    size === "lg" ? { px: 52, text: "text-3xl" } :
    size === "md" ? { px: 38, text: "text-xl" } :
                   { px: 30, text: "text-base" };

  return (
    <Link href="/" className="flex items-center gap-3 nav-logo" style={{ textDecoration: "none" }}>
      <div
        className="shrink-0"
        style={{ width: dim.px, height: dim.px, borderRadius: size === "lg" ? "14px" : "9px", overflow: "hidden", flexShrink: 0 }}
      >
        <Image
          src="/logo.png"
          alt="NexVM"
          width={dim.px}
          height={dim.px}
          style={{ objectFit: "cover", width: "100%", height: "100%" }}
          priority
        />
      </div>
      {!collapsed && (
        <span className={`font-bold ${dim.text}`} style={{ color: "var(--accent)" }}>
          NexVM
        </span>
      )}
    </Link>
  );
}
