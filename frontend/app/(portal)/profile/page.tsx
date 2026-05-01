import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { UserInfo, UserAnalytics } from "@/types";
import BackgroundLayer from "@/components/background-layer";
import ProfileClient from "@/components/profile-client";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export default async function ProfilePage() {
  const cookieStore = await cookies();
  const token = cookieStore.get("myvms_token")?.value;

  if (!token) redirect("/login");

  const headers = { Authorization: `Bearer ${token}` };

  const [meRes, analyticsRes] = await Promise.allSettled([
    fetch(`${BASE_URL}/api/v1/auth/me`, { headers }),
    fetch(`${BASE_URL}/api/v1/analytics/`, { headers }),
  ]);

  const profile: UserInfo | null =
    meRes.status === "fulfilled" && meRes.value.ok
      ? ((await meRes.value.json()) as UserInfo)
      : null;

  const analytics: UserAnalytics | null =
    analyticsRes.status === "fulfilled" && analyticsRes.value.ok
      ? ((await analyticsRes.value.json()) as UserAnalytics)
      : null;

  return (
    <div className="relative min-h-screen" style={{ background: "var(--bg)" }}>
      <BackgroundLayer />
      <div className="relative z-10 max-w-3xl mx-auto px-6 py-8">
        <ProfileClient profile={profile} analytics={analytics} />
      </div>
    </div>
  );
}
