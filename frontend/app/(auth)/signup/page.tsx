"use client";

import { useState } from "react";
import Link from "next/link";
import { setAuth } from "@/lib/auth";
import Logo from "@/components/Logo";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const validate = () => {
    if (password.length < 8) return "Password must be at least 8 characters";
    if (!/\d/.test(password)) return "Password must contain a number";
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);

    const validationError = validate();
    if (validationError) { setError(validationError); return; }

    setLoading(true);

    try {
      const res = await fetch(`${BASE_URL}/api/v1/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.detail ?? "Signup failed");
        setLoading(false);
        return;
      }

      if (data.access_token) {
        setAuth(data.access_token);
        window.location.href = "/vms";
      } else {
        setMessage(data.message ?? "Account created! Check your email or try signing in.");
        setLoading(false);
      }
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
          <h1 className="text-xl font-semibold tracking-tight" style={{ color: "var(--text)" }}>Create an account</h1>
          <p className="text-sm mt-1 mb-6" style={{ color: "var(--text-muted)" }}>Your VMs and Autopilot runs are private to your account.</p>

          {error && (
            <div
              className="mb-4 p-3 rounded text-sm"
              style={{ background: "color-mix(in srgb, var(--warning) 10%, transparent)", color: "var(--warning)", border: "1px solid color-mix(in srgb, var(--warning) 20%, transparent)" }}
            >
              {error}
            </div>
          )}

          {message && (
            <div
              className="mb-4 p-3 rounded text-sm"
              style={{ background: "color-mix(in srgb, var(--success) 10%, transparent)", color: "var(--success)", border: "1px solid color-mix(in srgb, var(--success) 20%, transparent)" }}
            >
              {message}
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
                placeholder="Min 8 chars, include a number"
              />
            </div>

            <button type="submit" disabled={loading} className="btn btn-primary w-full mt-2">
              {loading ? "Creating account…" : "Create account"}
            </button>
          </form>

          <p className="text-sm text-center mt-6" style={{ color: "var(--text-muted)" }}>
            Already have an account?{" "}
            <Link href="/login" style={{ color: "var(--accent)" }} className="hover:underline font-medium">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
