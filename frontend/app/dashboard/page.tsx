import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import Link from "next/link";
import LogoutButton from "./logout-button";
import { UserAnalytics } from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export default async function DashboardPage() {
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

  const {
    data: { session },
  } = await supabase.auth.getSession();

  let analytics: UserAnalytics | null = null;
  try {
    const res = await fetch(`${BASE_URL}/api/v1/analytics`, {
      headers: { Authorization: `Bearer ${session?.access_token}` },
    });
    if (res.ok) analytics = (await res.json()) as UserAnalytics;
  } catch {
    // fall through — analytics stays null, UI shows "—"
  }

  const fmt = (n: number | undefined) => (n !== undefined ? String(n) : "—");

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold">
          Dashboard — welcome, {user.email}
        </h1>
        <div className="flex items-center gap-4">
          {profile?.is_admin && (
            <Link
              href="/admin"
              className="text-sm font-medium text-blue-600 hover:underline"
            >
              Admin
            </Link>
          )}
          <LogoutButton />
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
        {[
          { label: "Total VMs", value: fmt(analytics?.total_vms) },
          { label: "Running", value: fmt(analytics?.running_vms) },
          { label: "Stopped", value: fmt(analytics?.stopped_vms) },
          { label: "Errors", value: fmt(analytics?.error_vms) },
          { label: "AI Commands", value: fmt(analytics?.total_ai_commands) },
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

      <Link
        href="/vms"
        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm font-medium inline-block"
      >
        Go to VMs
      </Link>
    </div>
  );
}
