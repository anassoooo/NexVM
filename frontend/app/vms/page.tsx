import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import { VM } from "@/types";
import VMsClient from "@/components/vms-client";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export default async function VMsPage() {
  const supabase = await createClient();

  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    redirect("/login");
  }

  let initialVms: VM[] = [];

  try {
    const res = await fetch(`${BASE_URL}/api/v1/vm/`, {
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
      },
    });
    if (res.ok) {
      initialVms = (await res.json()) as VM[];
    }
  } catch {
    // will show empty state; client will retry
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      <VMsClient initialVms={initialVms} />
    </div>
  );
}
