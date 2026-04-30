"use client";

import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import BackgroundLayer from "@/components/background-layer";
import { setAuth } from "@/lib/auth";

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
      setAuth(data.access_token, data.user.is_admin);
      window.location.href = data.user.is_admin ? "/admin" : "/ai";
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
      <BackgroundLayer />

      <div className="relative z-10 w-full max-w-sm px-4">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold" style={{ color: "var(--accent)" }}>myVMS</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>Virtual Machine Management</p>
        </div>

        <div className="glass" style={{ padding: "2rem" }}>
          <h2 className="text-xl font-bold mb-6 text-center" style={{ color: "var(--text)" }}>
            Sign In
          </h2>

          {sessionExpired && (
            <div
              role="alert"
              className="mb-4 p-3 rounded text-sm"
              style={{ background: "rgba(255,109,0,0.1)", color: "var(--warning)", border: "1px solid rgba(255,109,0,0.2)" }}
            >
              Your session has expired. Please log in again.
            </div>
          )}

          {error && (
            <div
              className="mb-4 p-3 rounded text-sm"
              style={{ background: "rgba(255,109,0,0.1)", color: "var(--warning)", border: "1px solid rgba(255,109,0,0.2)" }}
            >
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-medium mb-2 uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="input-dark"
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label className="block text-xs font-medium mb-2 uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="input-dark"
                placeholder="••••••••"
              />
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full mt-2">
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </form>

          <p className="text-sm text-center mt-6" style={{ color: "var(--text-muted)" }}>
            No account?{" "}
            <Link href="/signup" style={{ color: "var(--accent)" }} className="hover:underline font-medium">
              Sign up
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
