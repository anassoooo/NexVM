"use client";

import { AnalyticsTimeSeries, UserAnalytics } from "@/types";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

interface AnalyticsClientProps {
  analytics: UserAnalytics | null;
  timeseries: AnalyticsTimeSeries | null;
}

export default function AnalyticsClient({ analytics, timeseries }: AnalyticsClientProps) {
  return (
    <>
      <h1 className="text-2xl font-bold mb-6" style={{ color: "var(--text)" }}>
        Analytics
      </h1>

      {analytics && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 mb-8">
          <StatCard label="Total VMs" value={analytics.total_vms} />
          <StatCard label="Running" value={analytics.running_vms} color="var(--success)" />
          <StatCard label="Stopped" value={analytics.stopped_vms} />
          <StatCard label="Errors" value={analytics.error_vms} color={analytics.error_vms > 0 ? "var(--warning)" : undefined} />
          <StatCard label="AI Commands" value={analytics.total_ai_commands} />
        </div>
      )}

      {timeseries && (
        <div className="space-y-8">
          <ChartCard title="VM Count Over Time">
            <AreaChart data={timeseries.vms_by_day}>
              <defs>
                <linearGradient id="vmGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00e676" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#00e676" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#7a9e8a" }} tickFormatter={(v: string) => v.slice(5)} />
              <YAxis tick={{ fontSize: 10, fill: "#7a9e8a" }} allowDecimals={false} />
              <Tooltip contentStyle={{ background: "#0d1210", border: "1px solid rgba(0,230,118,0.2)", borderRadius: "8px", fontSize: 12 }} labelStyle={{ color: "#7a9e8a" }} itemStyle={{ color: "#00e676" }} />
              <Area type="monotone" dataKey="count" stroke="#00e676" fill="url(#vmGrad)" strokeWidth={2} />
            </AreaChart>
          </ChartCard>

          <ChartCard title="VMs Created Per Day">
            <BarChart data={timeseries.vms_created}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#7a9e8a" }} tickFormatter={(v: string) => v.slice(5)} />
              <YAxis tick={{ fontSize: 10, fill: "#7a9e8a" }} allowDecimals={false} />
              <Tooltip contentStyle={{ background: "#0d1210", border: "1px solid rgba(0,230,118,0.2)", borderRadius: "8px", fontSize: 12 }} labelStyle={{ color: "#7a9e8a" }} itemStyle={{ color: "#00e676" }} />
              <Bar dataKey="count" fill="#00e676" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ChartCard>

          <ChartCard title="AI Commands Per Day">
            <BarChart data={timeseries.ai_commands_by_day}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#7a9e8a" }} tickFormatter={(v: string) => v.slice(5)} />
              <YAxis tick={{ fontSize: 10, fill: "#7a9e8a" }} allowDecimals={false} />
              <Tooltip contentStyle={{ background: "#0d1210", border: "1px solid rgba(100,180,255,0.2)", borderRadius: "8px", fontSize: 12 }} labelStyle={{ color: "#7a9e8a" }} itemStyle={{ color: "#64b4ff" }} />
              <Bar dataKey="count" fill="#64b4ff" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ChartCard>
        </div>
      )}
    </>
  );
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="glass" style={{ padding: "1.5rem" }}>
      <h2 className="text-sm font-semibold mb-4" style={{ color: "var(--text-muted)" }}>
        {title}
      </h2>
      <ResponsiveContainer width="100%" height={220}>
        {children as React.ReactElement}
      </ResponsiveContainer>
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: number | string; color?: string }) {
  return (
    <div className="glass text-center" style={{ padding: "1rem" }}>
      <p className="text-2xl font-bold" style={{ color: color ?? "var(--text)" }}>{value}</p>
      <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>{label}</p>
    </div>
  );
}
