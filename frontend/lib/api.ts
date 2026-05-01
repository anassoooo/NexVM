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

  // 401 = invalid/expired token  |  403 = missing token (HTTPBearer raises 403)
  if (res.status === 401 || res.status === 403) return handleUnauthorized();

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed with status ${res.status}`);
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
