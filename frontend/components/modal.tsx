"use client";

import { useEffect } from "react";

interface ModalProps {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "warning";
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
}

export function Modal({
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "danger",
  onConfirm,
  onCancel,
  loading = false,
}: ModalProps) {
  const color  = variant === "danger" ? "var(--warning)" : "#ffc800";
  const border = variant === "danger" ? "rgba(255,109,0,0.4)" : "rgba(255,200,0,0.4)";
  const bg     = variant === "danger" ? "rgba(255,109,0,0.15)" : "rgba(255,200,0,0.12)";

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onCancel(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onCancel]);

  return (
    <div
      onClick={onCancel}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9998,
        background: "rgba(0,0,0,0.65)",
        backdropFilter: "blur(6px)",
        WebkitBackdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "1rem",
      }}
    >
      <div
        className="glass"
        onClick={(e) => e.stopPropagation()}
        style={{
          padding: "2rem",
          maxWidth: "420px",
          width: "100%",
          borderRadius: "14px",
          border: `1px solid ${border}`,
          boxShadow: `0 0 60px rgba(0,0,0,0.6)`,
        }}
      >
        {/* Icon */}
        <div style={{
          width: "44px",
          height: "44px",
          borderRadius: "50%",
          background: bg,
          border: `1px solid ${border}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          marginBottom: "1rem",
          fontSize: "20px",
          color,
        }}>
          ⚠
        </div>

        <h3 style={{ color: "var(--text)", fontWeight: "700", fontSize: "16px", marginBottom: "0.6rem" }}>
          {title}
        </h3>
        <p style={{ color: "var(--text-muted)", fontSize: "13px", lineHeight: 1.6, marginBottom: "1.75rem" }}>
          {message}
        </p>

        <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
          <button
            onClick={onCancel}
            style={{
              padding: "8px 22px",
              borderRadius: "999px",
              border: "1px solid rgba(255,255,255,0.1)",
              background: "transparent",
              color: "var(--text-muted)",
              fontSize: "13px",
              cursor: "pointer",
            }}
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            style={{
              padding: "8px 22px",
              borderRadius: "999px",
              border: `1px solid ${border}`,
              background: bg,
              color,
              fontSize: "13px",
              fontWeight: "600",
              cursor: loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.5 : 1,
            }}
          >
            {loading ? "…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
