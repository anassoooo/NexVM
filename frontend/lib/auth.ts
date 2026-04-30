const TOKEN_KEY = "myvms_token";
const ADMIN_KEY = "myvms_admin";
const MAX_AGE = 86400; // 24h — matches Supabase JWT expiry

export function setAuth(token: string, isAdmin: boolean): void {
  document.cookie = `${TOKEN_KEY}=${encodeURIComponent(token)}; path=/; SameSite=Lax; max-age=${MAX_AGE}`;
  document.cookie = `${ADMIN_KEY}=${isAdmin ? "1" : "0"}; path=/; SameSite=Lax; max-age=${MAX_AGE}`;
}

export function clearAuth(): void {
  document.cookie = `${TOKEN_KEY}=; path=/; max-age=0`;
  document.cookie = `${ADMIN_KEY}=; path=/; max-age=0`;
}

export function getTokenFromCookie(): string | null {
  if (typeof window === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${TOKEN_KEY}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}
