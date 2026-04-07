import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import AIChat from "@/components/ai-chat";

export default async function AIPage() {
  const supabase = await createClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-2">AI Assistant</h1>
      <p className="text-gray-500 text-sm mb-6">
        Describe what you want to do with your VMs in plain English.
      </p>
      <AIChat />
    </div>
  );
}
