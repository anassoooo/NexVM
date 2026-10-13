"use client";

import { clearAuth, getTokenFromCookie } from "@/lib/auth";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

function handleUnauthorized(): never {
  clearAuth();
  window.location.href = "/login?reason=session_expired";
  throw new Error("Session expired");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getTokenFromCookie();

  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (res.status === 401) return handleUnauthorized();

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    // Older FastAPI versions answer a missing token with 403 "Not authenticated".
    // Any other 403 (e.g. "Admin access required") is a permission error, not a logout.
    if (res.status === 403 && body.detail === "Not authenticated") return handleUnauthorized();
    throw new Error(formatDetail(body.detail) ?? `Request failed with status ${res.status}`);
  }

  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  delete: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "DELETE", body: JSON.stringify(body) }),
};

// FastAPI returns a string for HTTPException and a list of {msg} objects for 422s.
function formatDetail(detail: unknown): string | undefined {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((d) => (d && typeof d === "object" && "msg" in d ? String(d.msg) : null))
      .filter((m): m is string => !!m)
      .map((m) => m.replace(/^Value error, /, ""));
    return messages.length ? messages.join("; ") : undefined;
  }
  return undefined;
}
