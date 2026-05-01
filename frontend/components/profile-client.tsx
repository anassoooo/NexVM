"use client";

import { UserAnalytics, UserInfo } from "@/types";
import { api } from "@/lib/api";
import { useEffect, useState } from "react";

interface ProfileClientProps {
  profile: UserInfo | null;
  analytics: UserAnalytics | null;
}

export default function ProfileClient({ profile, analytics: initialAnalytics }: ProfileClientProps) {
  const [analytics, setAnalytics] = useState<UserAnalytics | null>(initialAnalytics);
  const [me, setMe] = useState<UserInfo | null>(profile);

  useEffect(() => {
    if (!me) {
      api.get<UserInfo>("/api/v1/auth/me").then(setMe).catch(() => {});
    }
    if (!initialAnalytics) {
      api.get<UserAnalytics>("/api/v1/analytics/").then(setAnalytics).catch(() => {});
    }
  }, [me, initialAnalytics]);

  if (!me) {
    return (
      <div className="glass" style={{ padding: "2rem" }}>
        <p style={{ color: "var(--text-muted)" }}>Loading profile…</p>
      </div>
    );
  }

  return (
    <>
      <h1 className="text-2xl font-bold mb-6" style={{ color: "var(--text)" }}>
        Profile
      </h1>

      <div className="glass mb-6" style={{ padding: "1.5rem" }}>
        <div className="grid gap-4">
          <ProfileField label="Email" value={me.email} />
          <ProfileField label="User ID" value={me.id} mono />
          <ProfileField
            label="Role"
            value={me.is_admin ? "Admin" : "User"}
            badge={me.is_admin ? "admin" : undefined}
          />
        </div>
      </div>

      {analytics && (
        <>
          <h2 className="text-lg font-semibold mb-4" style={{ color: "var(--text)" }}>
            Your Stats
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
            <StatCard label="VMs" value={analytics.total_vms} />
            <StatCard label="Running" value={analytics.running_vms} color="var(--success)" />
            <StatCard label="Stopped" value={analytics.stopped_vms} />
            <StatCard label="Errors" value={analytics.error_vms} color={analytics.error_vms > 0 ? "var(--warning)" : undefined} />
          </div>

          <div className="grid grid-cols-2 gap-4 mb-6">
            <StatCard label="AI Commands" value={analytics.total_ai_commands} />
            <StatCard
              label="Disk Usage"
              value={`${(analytics.total_disk_used_mb / 1024).toFixed(1)} / ${(analytics.disk_quota_mb / 1024).toFixed(0)} GB`}
            />
          </div>

          <div className="glass" style={{ padding: "1rem" }}>
            <div className="flex justify-between text-xs mb-2" style={{ color: "var(--text-muted)" }}>
              <span>Disk Quota</span>
              <span>
                {((analytics.total_disk_used_mb / analytics.disk_quota_mb) * 100).toFixed(1)}%
              </span>
            </div>
            <div style={{ background: "rgba(255,255,255,0.06)", borderRadius: "4px", overflow: "hidden", height: "8px" }}>
              <div
                style={{
                  width: `${Math.min(100, (analytics.total_disk_used_mb / analytics.disk_quota_mb) * 100).toFixed(1)}%`,
                  height: "100%",
                  background: analytics.total_disk_used_mb / analytics.disk_quota_mb > 0.9 ? "var(--warning)" : "var(--accent)",
                  transition: "width 0.3s",
                }}
              />
            </div>
          </div>
        </>
      )}
    </>
  );
}

function ProfileField({ label, value, mono, badge }: { label: string; value: string; mono?: boolean; badge?: string }) {
  return (
    <div className="flex items-center justify-between py-2" style={{ borderBottom: "1px solid rgba(0,230,118,0.06)" }}>
      <span className="text-sm" style={{ color: "var(--text-muted)" }}>{label}</span>
      {badge ? (
        <span
          className="text-xs font-semibold px-3 py-1 rounded-full"
          style={{
            background: badge === "admin" ? "rgba(0,230,118,0.12)" : "rgba(255,255,255,0.06)",
            color: badge === "admin" ? "var(--accent)" : "var(--text)",
            border: `1px solid ${badge === "admin" ? "rgba(0,230,118,0.25)" : "rgba(255,255,255,0.1)"}`,
          }}
        >
          {value}
        </span>
      ) : (
        <span
          className="text-sm"
          style={{ color: "var(--text)", fontFamily: mono ? "monospace" : "inherit", fontSize: mono ? "11px" : undefined }}
        >
          {value}
        </span>
      )}
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: number | string; color?: string }) {
  return (
    <div className="glass text-center" style={{ padding: "1rem" }}>
      <p className="text-2xl font-bold" style={{ color: color ?? "var(--text)" }}>
        {value}
      </p>
      <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>{label}</p>
    </div>
  );
}
