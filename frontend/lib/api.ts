"use client";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)myvms_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

function handleUnauthorized(): never {
  document.cookie = "myvms_token=; path=/; max-age=0";
  document.cookie = "myvms_admin=; path=/; max-age=0";
  window.location.href = "/login?reason=session_expired";
  throw new Error("Session expired");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();

  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (res.status === 401) return handleUnauthorized();

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
};
