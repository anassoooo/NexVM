"use client";

import { useState } from "react";
import Link from "next/link";
import BackgroundLayer from "@/components/background-layer";
import { setAuth } from "@/lib/auth";

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
        setAuth(data.access_token, data.user.is_admin);
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
      <BackgroundLayer />

      <div className="relative z-10 w-full max-w-sm px-4">
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo.png" alt="NexVM" width={72} height={72} style={{ borderRadius: "18px", objectFit: "cover" }} />
          </div>
          <h1 className="text-3xl font-bold" style={{ color: "var(--accent)" }}>NexVM</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>Virtual Machine Management</p>
        </div>

        <div className="glass" style={{ padding: "2rem" }}>
          <h2 className="text-xl font-bold mb-6 text-center" style={{ color: "var(--text)" }}>
            Create Account
          </h2>

          {error && (
            <div
              className="mb-4 p-3 rounded text-sm"
              style={{ background: "rgba(255,109,0,0.1)", color: "var(--warning)", border: "1px solid rgba(255,109,0,0.2)" }}
            >
              {error}
            </div>
          )}

          {message && (
            <div
              className="mb-4 p-3 rounded text-sm"
              style={{ background: "rgba(0,200,83,0.1)", color: "var(--success)", border: "1px solid rgba(0,200,83,0.2)" }}
            >
              {message}
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
                placeholder="Min 8 chars, include a number"
              />
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full mt-2">
              {loading ? "Creating account..." : "Sign Up"}
            </button>
          </form>

          <p className="text-sm text-center mt-6" style={{ color: "var(--text-muted)" }}>
            Already have an account?{" "}
            <Link href="/login" style={{ color: "var(--accent)" }} className="hover:underline font-medium">
              Log in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
