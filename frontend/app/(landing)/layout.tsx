import Link from "next/link";
import Logo from "@/components/Logo";
import ThemeToggle from "@/components/theme-toggle";
import { buttonClass } from "@/components/ui";

export default function LandingLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <nav
        className="sticky top-0 z-50"
        style={{ background: "var(--chrome)", backdropFilter: "blur(8px)", WebkitBackdropFilter: "blur(8px)", borderBottom: "1px solid var(--border)" }}
      >
        <div className="max-w-6xl mx-auto flex items-center justify-between gap-2 px-5 sm:px-8" style={{ height: 60 }}>
          <Logo size="md" />
          <div className="flex items-center gap-2 sm:gap-3 shrink-0">
            <ThemeToggle />
            <Link href="/login" className={buttonClass({ variant: "ghost" })}>Sign in</Link>
            {/* Shorter label on phones so the header fits at 320 px. */}
            <Link href="/signup" className={buttonClass({ variant: "primary" })}>
              <span className="sm:hidden">Sign up</span>
              <span className="hidden sm:inline">Create an account</span>
            </Link>
          </div>
        </div>
      </nav>
      {children}
    </>
  );
}
