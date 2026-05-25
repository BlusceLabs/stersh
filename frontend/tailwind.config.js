import type { Config } from "tailwindcss";
import { fontFamily } from "tailwindcss/defaultTheme";
import animatePlugin from "tailwindcss-animate";
import formsPlugin from "@tailwindcss/forms";
import typographyPlugin from "@tailwindcss/typography";

export default {
  // Enable class-based dark mode (controlled via <html class="dark">)
  darkMode: "class",

  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],

  theme: {
    extend: {
      // --- Brand Colors ---
      colors: {
        brand: {
          50:  "hsl(var(--color-brand-50) / <alpha-value>)",
          100: "hsl(var(--color-brand-100) / <alpha-value>)",
          200: "hsl(var(--color-brand-200) / <alpha-value>)",
          300: "hsl(var(--color-brand-300) / <alpha-value>)",
          400: "hsl(var(--color-brand-400) / <alpha-value>)",
          500: "hsl(var(--color-brand-500) / <alpha-value>)",
          600: "hsl(var(--color-brand-600) / <alpha-value>)",
          700: "hsl(var(--color-brand-700) / <alpha-value>)",
          800: "hsl(var(--color-brand-800) / <alpha-value>)",
          900: "hsl(var(--color-brand-900) / <alpha-value>)",
          950: "hsl(var(--color-brand-950) / <alpha-value>)",
        },
        // Semantic surface tokens — driven by CSS variables for dark mode
        surface: {
          DEFAULT:  "hsl(var(--surface) / <alpha-value>)",
          raised:   "hsl(var(--surface-raised) / <alpha-value>)",
          overlay:  "hsl(var(--surface-overlay) / <alpha-value>)",
          sunken:   "hsl(var(--surface-sunken) / <alpha-value>)",
        },
        border: {
          DEFAULT: "hsl(var(--border) / <alpha-value>)",
          strong:  "hsl(var(--border-strong) / <alpha-value>)",
        },
        text: {
          DEFAULT:  "hsl(var(--text) / <alpha-value>)",
          muted:    "hsl(var(--text-muted) / <alpha-value>)",
          inverted: "hsl(var(--text-inverted) / <alpha-value>)",
        },
      },

      // --- Typography ---
      fontFamily: {
        sans:  ["Inter Variable", ...fontFamily.sans],
        mono:  ["JetBrains Mono Variable", ...fontFamily.mono],
      },
      fontSize: {
        "2xs": ["0.625rem", { lineHeight: "0.875rem" }],
      },
      letterSpacing: {
        tighter: "-0.04em",
      },

      // --- Spacing & Sizing ---
      spacing: {
        "4.5": "1.125rem",
        "13":  "3.25rem",
        "15":  "3.75rem",
        "18":  "4.5rem",
        "112": "28rem",
        "128": "32rem",
      },
      maxWidth: {
        "8xl": "88rem",
        "9xl": "96rem",
      },
      borderRadius: {
        "4xl": "2rem",
      },

      // --- Shadows (CSS-variable-driven for dark mode) ---
      boxShadow: {
        subtle:   "0 1px 2px 0 hsl(var(--shadow-color) / 0.05)",
        card:     "0 2px 8px -1px hsl(var(--shadow-color) / 0.08), 0 1px 3px -1px hsl(var(--shadow-color) / 0.06)",
        elevated: "0 8px 24px -4px hsl(var(--shadow-color) / 0.12), 0 4px 8px -2px hsl(var(--shadow-color) / 0.08)",
        modal:    "0 24px 48px -12px hsl(var(--shadow-color) / 0.18)",
      },

      // --- Animations ---
      keyframes: {
        "fade-in": {
          from: { opacity: "0" },
          to:   { opacity: "1" },
        },
        "fade-out": {
          from: { opacity: "1" },
          to:   { opacity: "0" },
        },
        "slide-in-from-top": {
          from: { transform: "translateY(-0.5rem)", opacity: "0" },
          to:   { transform: "translateY(0)",       opacity: "1" },
        },
        "slide-in-from-bottom": {
          from: { transform: "translateY(0.5rem)", opacity: "0" },
          to:   { transform: "translateY(0)",      opacity: "1" },
        },
        "scale-in": {
          from: { transform: "scale(0.95)", opacity: "0" },
          to:   { transform: "scale(1)",    opacity: "1" },
        },
        "spin-slow": {
          from: { transform: "rotate(0deg)" },
          to:   { transform: "rotate(360deg)" },
        },
      },
      animation: {
        "fade-in":            "fade-in 0.2s ease-out",
        "fade-out":           "fade-out 0.2s ease-in",
        "slide-in-from-top":    "slide-in-from-top 0.25s ease-out",
        "slide-in-from-bottom": "slide-in-from-bottom 0.25s ease-out",
        "scale-in":           "scale-in 0.2s ease-out",
        "spin-slow":          "spin-slow 3s linear infinite",
      },
      transitionTimingFunction: {
        spring: "cubic-bezier(0.175, 0.885, 0.32, 1.275)",
      },

      // --- Z-index scale ---
      zIndex: {
        "60":  "60",
        "70":  "70",
        "80":  "80",
        "90":  "90",
        "100": "100",
      },
    },
  },

  plugins: [
    animatePlugin,   // tailwindcss-animate — data-[state] animation utilities
    formsPlugin,     // @tailwindcss/forms — sensible form resets
    typographyPlugin, // @tailwindcss/typography — prose styling
  ],
} satisfies Config;