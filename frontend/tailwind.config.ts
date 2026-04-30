import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        "cyber-bg":      "#0a0f0d",
        "cyber-accent":  "#00e676",
        "cyber-success": "#00c853",
        "cyber-warning": "#ff6d00",
        "cyber-muted":   "#7a9e8a",
        "cyber-text":    "#e8f5e9",
      },
      backdropBlur: {
        glass: "16px",
      },
      boxShadow: {
        glow:    "0 0 40px rgba(0,230,118,0.15)",
        "glow-sm": "0 0 20px rgba(0,230,118,0.10)",
        "glow-btn": "0 0 24px rgba(0,230,118,0.35)",
      },
      fontFamily: {
        sans: ["Space Grotesk", "Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
