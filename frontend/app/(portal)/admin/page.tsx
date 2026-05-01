import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { AdminAnalytics, UserInfo } from "@/types";
import BackgroundLayer from "@/components/background-layer";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export default async function AdminPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get("myvms_token")?.value;
  const isAdmin = cookieStore.get("myvms_admin")?.value === "1";

  if (!token) redirect("/login");
  if (!isAdmin) redirect("/ai");

  const headers = { Authorization: `Bearer ${token}` };

  const [analyticsRes, meRes] = await Promise.allSettled([
    fetch(`${BASE_URL}/api/v1/analytics/admin`, { headers }),
    fetch(`${BASE_URL}/api/v1/auth/me`, { headers }),
  ]);

  const analytics: AdminAnalytics | null =
    analyticsRes.status === "fulfilled" && analyticsRes.value.ok
      ? ((await analyticsRes.value.json()) as AdminAnalytics)
      : null;

  const me: UserInfo | null =
    meRes.status === "fulfilled" && meRes.value.ok
      ? ((await meRes.value.json()) as UserInfo)
      : null;

  const fmt = (n: number | undefined) => (n !== undefined ? String(n) : "—");

  const summaryCards = [
    { label: "Total Users",       value: fmt(analytics?.total_users) },
    { label: "Total VMs",         value: fmt(analytics?.total_vms) },
    { label: "Total AI Commands", value: fmt(analytics?.total_ai_commands) },
  ];

  const statusCards = [
    { label: "Running", value: fmt(analytics?.running_vms), color: "var(--success)" },
    { label: "Stopped", value: fmt(analytics?.stopped_vms), color: "var(--warning)" },
    { label: "Error",   value: fmt(analytics?.error_vms),   color: "var(--warning)" },
  ];

  return (
    <div className="relative min-h-screen" style={{ background: "var(--bg)" }}>
      <BackgroundLayer />

      <div className="relative z-10 max-w-4xl mx-auto px-6 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>
            Admin Dashboard
          </h1>
          {me?.email && (
            <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>{me.email}</p>
          )}
        </div>

        <p className="text-xs font-semibold uppercase tracking-widest mb-4" style={{ color: "var(--text-muted)" }}>
          System Summary
        </p>
        <div className="grid grid-cols-3 gap-4 mb-10">
          {summaryCards.map(({ label, value }) => (
            <div key={label} className="glass text-center" style={{ padding: "1.5rem 1rem" }}>
              <p className="text-3xl font-bold" style={{ color: "var(--accent)" }}>{value}</p>
              <p className="text-xs mt-2" style={{ color: "var(--text-muted)" }}>{label}</p>
            </div>
          ))}
        </div>

        <p className="text-xs font-semibold uppercase tracking-widest mb-4" style={{ color: "var(--text-muted)" }}>
          VM Status
        </p>
        <div className="grid grid-cols-3 gap-4 mb-10">
          {statusCards.map(({ label, value, color }) => (
            <div key={label} className="glass text-center" style={{ padding: "1.5rem 1rem" }}>
              <p className="text-3xl font-bold" style={{ color }}>{value}</p>
              <p className="text-xs mt-2" style={{ color: "var(--text-muted)" }}>{label}</p>
            </div>
          ))}
        </div>

        <p className="text-xs font-semibold uppercase tracking-widest mb-4" style={{ color: "var(--text-muted)" }}>
          Disk Usage
        </p>
        {analytics ? (() => {
          const usedMb   = analytics.total_disk_used_mb;
          const quotaMb  = analytics.disk_quota_mb;
          const pct      = quotaMb > 0 ? Math.min(100, (usedMb / quotaMb) * 100) : 0;
          const usedGb   = (usedMb  / 1024).toFixed(1);
          const quotaGb  = (quotaMb / 1024).toFixed(1);
          const barColor = pct > 90 ? "var(--warning)" : "var(--accent)";
          return (
            <div className="glass" style={{ padding: "1.5rem" }}>
              <div className="flex justify-between text-xs mb-2" style={{ color: "var(--text-muted)" }}>
                <span>{usedGb} GB used</span>
                <span>{quotaGb} GB quota</span>
              </div>
              <div style={{ background: "rgba(255,255,255,0.06)", borderRadius: "4px", overflow: "hidden", height: "8px" }}>
                <div style={{ width: `${pct.toFixed(1)}%`, height: "100%", background: barColor, transition: "width 0.3s" }} />
              </div>
              <p className="text-xs mt-2 text-right" style={{ color: barColor }}>{pct.toFixed(1)}% used</p>
            </div>
          );
        })() : (
          <div className="glass" style={{ padding: "1.5rem" }}>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>Disk data unavailable</p>
          </div>
        )}
      </div>
    </div>
  );
}
