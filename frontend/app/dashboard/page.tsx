import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import Link from "next/link";
import LogoutButton from "./logout-button";

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
      <p className="text-gray-500">Your virtual machines will appear here.</p>
    </div>
  );
}
