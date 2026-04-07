import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import { AdminAnalytics } from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export default async function AdminPage() {
  const supabase = await createClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  const { data: profile } = await supabase
    .from("profiles")
    .select("is_admin")
    .eq("id", user.id)
    .single();

  if (!profile?.is_admin) {
    redirect("/dashboard");
  }

  const {
    data: { session },
  } = await supabase.auth.getSession();

  let analytics: AdminAnalytics | null = null;
  try {
    const res = await fetch(`${BASE_URL}/api/v1/analytics/admin`, {
      headers: { Authorization: `Bearer ${session?.access_token}` },
    });
    if (res.ok) analytics = (await res.json()) as AdminAnalytics;
  } catch {
    // fall through — analytics stays null, UI shows "—"
  }

  const fmt = (n: number | undefined) => (n !== undefined ? String(n) : "—");

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Admin Dashboard — {user.email}</h1>

      <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
        System Summary
      </h2>
      <div className="grid grid-cols-3 gap-4 mb-8">
        {[
          { label: "Total Users", value: fmt(analytics?.total_users) },
          { label: "Total VMs", value: fmt(analytics?.total_vms) },
          { label: "Total AI Commands", value: fmt(analytics?.total_ai_commands) },
        ].map(({ label, value }) => (
          <div
            key={label}
            className="bg-white border border-gray-200 rounded-lg p-4 text-center shadow-sm"
          >
            <p className="text-2xl font-bold text-gray-900">{value}</p>
            <p className="text-xs text-gray-500 mt-1">{label}</p>
          </div>
        ))}
      </div>

      <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
        VM Status
      </h2>
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Running", value: fmt(analytics?.running_vms) },
          { label: "Stopped", value: fmt(analytics?.stopped_vms) },
          { label: "Error", value: fmt(analytics?.error_vms) },
        ].map(({ label, value }) => (
          <div
            key={label}
            className="bg-white border border-gray-200 rounded-lg p-4 text-center shadow-sm"
          >
            <p className="text-2xl font-bold text-gray-900">{value}</p>
            <p className="text-xs text-gray-500 mt-1">{label}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
