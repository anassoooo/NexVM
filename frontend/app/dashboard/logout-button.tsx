"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

const supabase = createClient();

export default function LogoutButton() {
  const [error, setError] = useState<string | null>(null);

  const handleLogout = async () => {
    setError(null);
    const { error } = await supabase.auth.signOut();
    if (error) {
      setError("Sign out failed. Please try again.");
      return;
    }
    window.location.href = "/login";
  };

  return (
    <div className="flex flex-col items-end gap-1">
      {error && <p className="text-red-600 text-xs">{error}</p>}
      <button
        onClick={handleLogout}
        className="text-sm text-gray-600 hover:text-gray-900 border rounded px-3 py-1"
      >
        Log out
      </button>
    </div>
  );
}
