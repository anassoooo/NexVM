import Link from "next/link";
import Logo from "@/components/Logo";

export default function LandingLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <nav
        className="flex items-center justify-between px-6"
        style={{
          height: 56,
          background: "rgba(10,15,13,0.85)",
          backdropFilter: "blur(12px)",
          WebkitBackdropFilter: "blur(12px)",
          borderBottom: "1px solid var(--border)",
          position: "sticky",
          top: 0,
          zIndex: 50,
        }}
      >
        <Logo size="sm" />
        <div className="flex items-center gap-3">
          <Link href="/login" className="text-sm font-medium nav-link">
            Sign In
          </Link>
          <Link
            href="/signup"
            className="btn-primary"
            style={{ padding: "6px 18px", fontSize: "0.8rem" }}
          >
            Get Started
          </Link>
        </div>
      </nav>
      {children}
    </>
  );
}
