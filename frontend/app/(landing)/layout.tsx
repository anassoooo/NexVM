import Link from "next/link";
import Logo from "@/components/Logo";
import ThemeToggle from "@/components/theme-toggle";

export default function LandingLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <nav
        className="flex items-center justify-between px-6"
        style={{
          height: 56,
          background: "var(--chrome)",
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
          <ThemeToggle />
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
