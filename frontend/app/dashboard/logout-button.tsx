"use client";

import { clearAuth } from "@/lib/auth";

export default function LogoutButton() {
  const handleLogout = () => {
    clearAuth();
    window.location.href = "/login";
  };

  return (
    <button
      onClick={handleLogout}
      className="btn-primary"
      style={{ padding: "6px 18px", fontSize: "0.8rem" }}
    >
      Log out
    </button>
  );
}
