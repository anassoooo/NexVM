import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export default async function HomePage() {
  const cookieStore = await cookies();
  const token = cookieStore.get("myvms_token")?.value;
  const isAdmin = cookieStore.get("myvms_admin")?.value === "1";

  if (!token) redirect("/login");
  if (isAdmin) redirect("/admin");
  redirect("/ai");
}
