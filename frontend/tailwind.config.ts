import type { Config } from "tailwindcss";

// Colors come exclusively from the CSS custom properties in src/index.css —
// the §13 tokens are the source of truth, Tailwind just exposes them.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    colors: {
      transparent: "transparent",
      current: "currentColor",
      canvas: "var(--canvas)",
      surface: "var(--surface)",
      ink: "var(--ink)",
      "ink-muted": "var(--ink-muted)",
      "ink-faint": "var(--ink-faint)",
      rule: "var(--rule)",
      "rule-strong": "var(--rule-strong)",
      accent: "var(--accent)",
      "accent-wash": "var(--accent-wash)",
      positive: "var(--positive)",
      negative: "var(--negative)",
      attention: "var(--attention)",
      critical: "var(--critical)",
    },
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["'IBM Plex Mono'", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
