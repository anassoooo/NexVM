import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import { VM } from "@/types";
import VMsClient from "@/components/vms-client";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export default async function VMsPage() {
  const supabase = await createClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  const {
    data: { session },
  } = await supabase.auth.getSession();

  let initialVms: VM[] = [];

  try {
    const res = await fetch(`${BASE_URL}/api/v1/vm`, {
      headers: {
        Authorization: `Bearer ${session?.access_token}`,
        "Content-Type": "application/json",
      },
    });
    if (res.ok) {
      initialVms = (await res.json()) as VM[];
    }
  } catch (err) {
    console.error("Failed to fetch VMs:", err);
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      <VMsClient initialVms={initialVms} />
    </div>
  );
}
