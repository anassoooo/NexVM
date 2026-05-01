import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { AnalyticsTimeSeries, UserAnalytics } from "@/types";
import AnalyticsClient from "@/components/analytics-client";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export default async function AnalyticsPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get("nexvm_token")?.value;

  if (!token) redirect("/login");

  const headers = { Authorization: `Bearer ${token}` };

  const [analyticsRes, tsRes] = await Promise.allSettled([
    fetch(`${BASE_URL}/api/v1/analytics/`, { headers }),
    fetch(`${BASE_URL}/api/v1/analytics/timeseries?days=30`, { headers }),
  ]);

  const analytics: UserAnalytics | null =
    analyticsRes.status === "fulfilled" && analyticsRes.value.ok
      ? ((await analyticsRes.value.json()) as UserAnalytics)
      : null;

  const timeseries: AnalyticsTimeSeries | null =
    tsRes.status === "fulfilled" && tsRes.value.ok
      ? ((await tsRes.value.json()) as AnalyticsTimeSeries)
      : null;

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <AnalyticsClient analytics={analytics} timeseries={timeseries} />
    </div>
  );
}
