import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import AdminVMsClient from "@/components/admin-vms-client";
import { VM } from "@/types";
import BackgroundLayer from "@/components/background-layer";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export default async function AdminVMsPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get("myvms_token")?.value;
  const isAdmin = cookieStore.get("myvms_admin")?.value === "1";

  if (!token) redirect("/login");
  if (!isAdmin) redirect("/ai");

  let vms: VM[] = [];
  try {
    const res = await fetch(`${BASE_URL}/api/v1/admin/vm`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) vms = (await res.json()) as VM[];
  } catch {
    // fall through — empty state
  }

  return (
    <div className="relative min-h-screen" style={{ background: "var(--bg)" }}>
      <BackgroundLayer />
      <div className="relative z-10 max-w-6xl mx-auto px-6 py-8">
        <AdminVMsClient initialVms={vms} />
      </div>
    </div>
  );
}
