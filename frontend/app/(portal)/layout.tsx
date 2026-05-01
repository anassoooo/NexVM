"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clearAuth } from "@/lib/auth";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { UserInfo } from "@/types";

const NAV_ITEMS = [
  { href: "/ai", label: "AI Assistant", icon: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" },
  { href: "/vms", label: "Virtual Machines", icon: "M2 3h20v14H2z M8 21h8 M12 17v4" },
  { href: "/analytics", label: "Analytics", icon: "M18 20V10 M12 20V4 M6 20v-6" },
  { href: "/logs", label: "Activity Logs", icon: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z M14 2v6h6 M16 13H8 M16 17H8 M10 9H8" },
  { href: "/profile", label: "Profile", icon: "M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2 M12 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8z" },
];

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    api.get<UserInfo>("/api/v1/auth/me").then(setUser).catch(() => {});
  }, []);

  const isAdmin = typeof document !== "undefined" && document.cookie.includes("myvms_admin=1");

  function handleLogout() {
    clearAuth();
    window.location.href = "/login";
  }

  function getInitials(email: string) {
    return email.charAt(0).toUpperCase();
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside
        className="flex flex-col shrink-0 transition-all duration-200"
        style={{
          width: collapsed ? 68 : 240,
          background: "rgba(8,12,10,0.95)",
          borderRight: "1px solid var(--border)",
        }}
      >
        {/* Logo */}
        <div
          className="flex items-center gap-3 px-4 shrink-0"
          style={{ height: 56, borderBottom: "1px solid var(--border)" }}
        >
          <div
            className="shrink-0"
            style={{
              width: 32,
              height: 32,
              borderRadius: "8px",
              background: "rgba(0,230,118,0.12)",
              border: "1px solid rgba(0,230,118,0.25)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#00e676" strokeWidth="1.5">
              <rect x="2" y="3" width="20" height="14" rx="2" />
              <line x1="8" y1="21" x2="16" y2="21" />
              <line x1="12" y1="17" x2="12" y2="21" />
            </svg>
          </div>
          {!collapsed && (
            <span className="font-bold text-base" style={{ color: "var(--accent)" }}>
              myVMS
            </span>
          )}
        </div>

        {/* Nav links */}
        <nav className="flex-1 py-3 px-2 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                className="flex items-center gap-3 rounded-lg transition-colors"
                style={{
                  padding: collapsed ? "10px 0" : "10px 12px",
                  justifyContent: collapsed ? "center" : "flex-start",
                  background: active ? "rgba(0,230,118,0.08)" : "transparent",
                  color: active ? "var(--accent)" : "var(--text-muted)",
                  borderLeft: active && !collapsed ? "2px solid var(--accent)" : "2px solid transparent",
                }}
                title={collapsed ? item.label : undefined}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d={item.icon} />
                </svg>
                {!collapsed && <span className="text-sm font-medium">{item.label}</span>}
              </Link>
            );
          })}

          {isAdmin && (
            <>
              <div className="my-2" style={{ borderTop: "1px solid var(--border)" }} />
              <Link
                href="/admin"
                className="flex items-center gap-3 rounded-lg transition-colors"
                style={{
                  padding: collapsed ? "10px 0" : "10px 12px",
                  justifyContent: collapsed ? "center" : "flex-start",
                  background: pathname.startsWith("/admin") ? "rgba(255,109,0,0.08)" : "transparent",
                  color: pathname.startsWith("/admin") ? "var(--warning)" : "var(--text-muted)",
                  borderLeft: pathname.startsWith("/admin") && !collapsed ? "2px solid var(--warning)" : "2px solid transparent",
                }}
                title={collapsed ? "Admin Panel" : undefined}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
                {!collapsed && <span className="text-sm font-medium">Admin Panel</span>}
              </Link>
            </>
          )}
        </nav>

        {/* Collapse toggle */}
        <div className="px-2 pb-3 shrink-0">
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="flex items-center gap-2 w-full rounded-lg transition-colors"
            style={{
              padding: "8px 12px",
              justifyContent: collapsed ? "center" : "flex-start",
              color: "var(--text-muted)",
              background: "transparent",
              border: "none",
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              style={{ transform: collapsed ? "rotate(180deg)" : "none", transition: "transform 0.2s" }}
            >
              <path d="M15 18l-6-6 6-6" />
            </svg>
            {!collapsed && <span className="text-xs">Collapse</span>}
          </button>
        </div>
      </aside>

      {/* Main area */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Header */}
        <header
          className="flex items-center justify-between px-6 shrink-0"
          style={{
            height: 56,
            background: "rgba(10,15,13,0.8)",
            borderBottom: "1px solid var(--border)",
          }}
        >
          <div>
            <h1 className="text-sm font-semibold" style={{ color: "var(--text)" }}>
              {NAV_ITEMS.find((i) => pathname === i.href || pathname.startsWith(i.href + "/"))?.label ?? "Dashboard"}
            </h1>
          </div>

          <div className="flex items-center gap-4">
            {/* User avatar + dropdown */}
            <div className="flex items-center gap-3">
              <Link href="/profile" className="flex items-center gap-3" style={{ textDecoration: "none" }}>
                <div
                  className="flex items-center justify-center font-bold text-sm"
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: "50%",
                    background: "rgba(0,230,118,0.12)",
                    border: "1px solid rgba(0,230,118,0.25)",
                    color: "var(--accent)",
                  }}
                >
                  {user ? getInitials(user.email) : "?"}
                </div>
                {!collapsed && (
                  <div className="hidden sm:block">
                    <p className="text-xs font-medium" style={{ color: "var(--text)" }}>
                      {user?.email ?? "Loading..."}
                    </p>
                    <p className="text-xs" style={{ color: user?.is_admin ? "var(--warning)" : "var(--text-muted)", fontSize: "10px" }}>
                      {user?.is_admin ? "Admin" : "User"}
                    </p>
                  </div>
                )}
              </Link>
              <button
                onClick={handleLogout}
                className="text-xs font-medium px-3 py-1.5 rounded-lg transition-colors"
                style={{
                  color: "var(--text-muted)",
                  background: "rgba(255,255,255,0.04)",
                  border: "1px solid rgba(255,255,255,0.06)",
                  cursor: "pointer",
                  fontFamily: "inherit",
                }}
              >
                Logout
              </button>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto" style={{ background: "var(--bg)" }}>
          {children}
        </main>
      </div>
    </div>
  );
}
