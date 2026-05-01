import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { UserAnalytics, VM } from "@/types";
import VMsClient from "@/components/vms-client";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export default async function VMsPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get("myvms_token")?.value;

  if (!token) redirect("/login");

  const headers = { Authorization: `Bearer ${token}` };

  const [vmsRes, analyticsRes] = await Promise.allSettled([
    fetch(`${BASE_URL}/api/v1/vm`, { headers }),
    fetch(`${BASE_URL}/api/v1/analytics/`, { headers }),
  ]);

  const vms: VM[] =
    vmsRes.status === "fulfilled" && vmsRes.value.ok
      ? ((await vmsRes.value.json()) as VM[])
      : [];

  const analytics: UserAnalytics | null =
    analyticsRes.status === "fulfilled" && analyticsRes.value.ok
      ? ((await analyticsRes.value.json()) as UserAnalytics)
      : null;

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <VMsClient initialVms={vms} initialAnalytics={analytics} />
    </div>
  );
}
