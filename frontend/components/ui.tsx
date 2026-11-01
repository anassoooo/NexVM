// Shared building blocks. Styles live in globals.css (.btn, .badge, .card, .tone-*).

import type { ButtonHTMLAttributes, HTMLAttributes } from "react";

export type Tone = "neutral" | "accent" | "info" | "warning" | "danger" | "caution";
type Variant = "primary" | "secondary" | "danger" | "ghost" | "tone";

/** Class names for a button, also for links styled as buttons. */
export function buttonClass({ variant = "secondary", size = "md", tone }: { variant?: Variant; size?: "sm" | "md"; tone?: Tone } = {}) {
  return ["btn", `btn-${variant}`, size === "sm" && "btn-sm", tone && `tone-${tone}`].filter(Boolean).join(" ");
}

export function Button({
  variant, size, tone, className = "", type = "button", ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: "sm" | "md"; tone?: Tone }) {
  return <button type={type} className={`${buttonClass({ variant, size, tone })} ${className}`} {...props} />;
}

export function Badge({ tone = "neutral", className = "", ...props }: HTMLAttributes<HTMLSpanElement> & { tone?: Tone }) {
  return <span className={`badge tone-${tone} ${className}`} {...props} />;
}

export function Card({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={`card ${className}`} {...props} />;
}
