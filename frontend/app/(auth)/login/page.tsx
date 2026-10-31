"use client";

import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { setAuth } from "@/lib/auth";
import Logo from "@/components/Logo";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const searchParams = useSearchParams();
  const sessionExpired = searchParams.get("reason") === "session_expired";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await fetch(`${BASE_URL}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (res.status === 429) {
        setError("Too many login attempts. Please try again later.");
        setLoading(false);
        return;
      }

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body.detail ?? "Invalid email or password");
        setLoading(false);
        return;
      }

      const data = await res.json();
      setAuth(data.access_token);
      window.location.href = data.user.is_admin ? "/admin" : "/vms";
    } catch {
      setError("Something went wrong. Please try again.");
      setLoading(false);
    }
  };

  return (
    <div
      className="relative min-h-screen flex items-center justify-center"
      style={{ background: "var(--bg)", zIndex: 1 }}
    >

      <div className="relative z-10 w-full max-w-sm px-4">
        <div className="mb-6">
          <Logo size="md" />
        </div>

        <div className="card" style={{ padding: "1.75rem" }}>
          <h1 className="text-xl font-semibold tracking-tight" style={{ color: "var(--text)" }}>Sign in</h1>
          <p className="text-sm mt-1 mb-6" style={{ color: "var(--text-muted)" }}>Plan and approve changes to your VirtualBox VMs.</p>

          {sessionExpired && (
            <div
              role="alert"
              className="mb-4 p-3 rounded text-sm"
              style={{ background: "color-mix(in srgb, var(--warning) 10%, transparent)", color: "var(--warning)", border: "1px solid color-mix(in srgb, var(--warning) 20%, transparent)" }}
            >
              Your session has expired. Please log in again.
            </div>
          )}

          {error && (
            <div
              className="mb-4 p-3 rounded text-sm"
              style={{ background: "color-mix(in srgb, var(--warning) 10%, transparent)", color: "var(--warning)", border: "1px solid color-mix(in srgb, var(--warning) 20%, transparent)" }}
            >
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="field"
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="field"
                placeholder="••••••••"
              />
            </div>

            <button type="submit" disabled={loading} className="btn btn-primary w-full mt-2">
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>

          <p className="text-sm text-center mt-6" style={{ color: "var(--text-muted)" }}>
            No account yet?{" "}
            <Link href="/signup" style={{ color: "var(--accent)" }} className="hover:underline font-medium">
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
