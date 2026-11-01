"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

type ToastType = "success" | "error" | "warning";

interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
}

const ToastContext = createContext<(type: ToastType, message: string) => void>(() => {});

export function useToast() {
  return useContext(ToastContext);
}

const STYLES: Record<ToastType, { bg: string; border: string; color: string; icon: string }> = {
  success: { bg: "color-mix(in srgb, var(--accent) 10%, transparent)", border: "color-mix(in srgb, var(--accent) 30%, transparent)", color: "var(--accent)",  icon: "✓" },
  error:   { bg: "color-mix(in srgb, var(--warning) 10%, transparent)", border: "color-mix(in srgb, var(--warning) 35%, transparent)", color: "var(--warning)", icon: "✕" },
  warning: { bg: "color-mix(in srgb, var(--caution) 10%, transparent)", border: "color-mix(in srgb, var(--caution) 30%, transparent)", color: "var(--caution)",         icon: "⚠" },
};

function ToastCard({ item, onDismiss }: { item: ToastItem; onDismiss: () => void }) {
  const [visible, setVisible] = useState(false);
  const s = STYLES[item.type];

  useEffect(() => {
    const enter = setTimeout(() => setVisible(true), 10);
    const leave = setTimeout(() => { setVisible(false); setTimeout(onDismiss, 300); }, 3800);
    return () => { clearTimeout(enter); clearTimeout(leave); };
  }, [onDismiss]);

  return (
    <div style={{
      background: s.bg,
      border: `1px solid ${s.border}`,
      borderRadius: "10px",
      padding: "10px 14px",
      display: "flex",
      alignItems: "center",
      gap: "10px",
      minWidth: "260px",
      maxWidth: "380px",
      backdropFilter: "blur(16px)",
      WebkitBackdropFilter: "blur(16px)",
      boxShadow: "var(--shadow-lg)",
      opacity: visible ? 1 : 0,
      transform: visible ? "translateX(0)" : "translateX(24px)",
      transition: "opacity 0.28s ease, transform 0.28s ease",
    }}>
      <span style={{ color: s.color, fontWeight: "bold", fontSize: "15px", flexShrink: 0 }}>{s.icon}</span>
      <span style={{ color: "var(--text)", fontSize: "13px", flex: 1, lineHeight: 1.45 }}>{item.message}</span>
      <button
        onClick={() => { setVisible(false); setTimeout(onDismiss, 300); }}
        style={{ color: "var(--text-muted)", background: "none", border: "none", cursor: "pointer", fontSize: "16px", lineHeight: 1, padding: "0 2px", flexShrink: 0 }}
      >×</button>
    </div>
  );
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const add = useCallback((type: ToastType, message: string) => {
    const id = Math.random().toString(36).slice(2, 9);
    setToasts((prev) => [...prev, { id, type, message }]);
  }, []);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={add}>
      {children}
      <div style={{
        position: "fixed",
        top: "70px",
        right: "16px",
        zIndex: 9999,
        display: "flex",
        flexDirection: "column",
        gap: "8px",
        pointerEvents: "none",
      }}>
        {toasts.map((t) => (
          <div key={t.id} style={{ pointerEvents: "auto" }}>
            <ToastCard item={t} onDismiss={() => dismiss(t.id)} />
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
