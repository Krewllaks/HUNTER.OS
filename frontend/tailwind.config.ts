import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      // ── HUNTER.OS Swiss-Minimalist Design Tokens ──────
      colors: {
        background: "#0f172a",         // navy bg
        surface: "#1e293b",            // navy card
        primary: "#4f8ef7",            // blue accent
        "primary-hover": "#3b7ef5",
        text: "#f1f5f9",               // slate-100
        "text-secondary": "#94a3b8",   // slate-400
        "text-muted": "#64748b",       // slate-500
        accent: "#4f8ef7",
        border: "#334155",             // slate-700
        "border-light": "#1e2d4a",     // dark border
        success: "#34d399",            // emerald-400
        warning: "#fbbf24",            // amber-400
        danger: "#f87171",             // red-400
        // Chart colors
        "chart-1": "#4f8ef7",
        "chart-2": "#38bdf8",
        "chart-3": "#818cf8",
        "chart-4": "#34d399",
        "chart-5": "#fb923c",
        // Dark card & sidebar
        "card-dark": "#0c1525",
        "card-dark-surface": "#1e293b",
        "sidebar-text": "#94a3b8",
        "sidebar-active": "#4f8ef7",
      },
      fontFamily: {
        display: ["Inter", '"Helvetica Neue"', "sans-serif"],
        body: ["Inter", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "monospace"],
      },
      fontSize: {
        // Swiss typography scale
        "display-xl": ["3.5rem", { lineHeight: "1.1", letterSpacing: "-0.03em", fontWeight: "700" }],
        "display-lg": ["2.5rem", { lineHeight: "1.15", letterSpacing: "-0.02em", fontWeight: "700" }],
        "display-md": ["2rem", { lineHeight: "1.2", letterSpacing: "-0.02em", fontWeight: "700" }],
        "display-sm": ["1.5rem", { lineHeight: "1.25", letterSpacing: "-0.01em", fontWeight: "700" }],
        "heading": ["1.125rem", { lineHeight: "1.4", letterSpacing: "-0.01em", fontWeight: "600" }],
        "body-lg": ["1rem", { lineHeight: "1.6", letterSpacing: "0" }],
        "body-md": ["0.875rem", { lineHeight: "1.6", letterSpacing: "0.01em" }],
        "body-sm": ["0.75rem", { lineHeight: "1.5", letterSpacing: "0.02em" }],
        "label": ["0.6875rem", { lineHeight: "1.3", letterSpacing: "0.08em", fontWeight: "600" }],
      },
      spacing: {
        // Swiss 8px baseline grid
        "grid-1": "0.5rem",   // 8px
        "grid-2": "1rem",     // 16px
        "grid-3": "1.5rem",   // 24px
        "grid-4": "2rem",     // 32px
        "grid-5": "2.5rem",   // 40px
        "grid-6": "3rem",     // 48px
        "grid-8": "4rem",     // 64px
        "grid-10": "5rem",    // 80px
        "grid-12": "6rem",    // 96px
        "sidebar": "16rem",   // 256px sidebar width
      },
      borderRadius: {
        "sm": "4px",
        "md": "8px",
        "lg": "12px",
      },
      boxShadow: {
        "card": "0 1px 3px rgba(0, 0, 0, 0.3), 0 1px 2px rgba(0, 0, 0, 0.2)",
        "card-hover": "0 4px 12px rgba(0, 0, 0, 0.4), 0 2px 4px rgba(0, 0, 0, 0.2)",
        "dropdown": "0 8px 24px rgba(0, 0, 0, 0.4)",
      },
      animation: {
        "stagger-in": "staggerIn 0.4s ease-out forwards",
        "slide-up": "slideUp 0.3s ease-out",
        "fade-in": "fadeIn 0.2s ease-out",
      },
      keyframes: {
        staggerIn: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
