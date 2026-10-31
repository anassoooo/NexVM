import Link from "next/link";
import Logo from "@/components/Logo";
import ThemeToggle from "@/components/theme-toggle";

export default function LandingLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <nav
        className="flex items-center justify-between gap-2 px-4 sm:px-6"
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
        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          <ThemeToggle />
          <Link href="/login" className="text-sm font-medium nav-link whitespace-nowrap">
            Sign In
          </Link>
          {/* Shorter label on phones so the header fits at 320 px. */}
          <Link
            href="/signup"
            className="btn-primary whitespace-nowrap"
            style={{ padding: "6px 14px", fontSize: "0.8rem" }}
          >
            <span className="sm:hidden">Sign up</span>
            <span className="hidden sm:inline">Get Started</span>
          </Link>
        </div>
      </nav>
      {children}
    </>
  );
}
