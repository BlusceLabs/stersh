/** @type {import('tailwindcss').Config} */
export default {
  // Broadened to explicitly capture Svelte, Qwik, and standard Astro layouts
  content: [
    './src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx}',
    './packages/*/src/**/*.{ts,tsx,js,jsx,svelte}',
  ],
  theme: {
    extend: {
      colors: {
        // Watchfy surface scale (mirrors src/styles/tokens.css)
        surface: {
          0: '#09090b',
          1: '#18181b',
          2: '#27272a',
          3: '#3f3f46',
        },

        // Brand identity — Watchfy premium dark slate system
        brand: {
          red: '#ef4444',
          'red-deep': '#dc2626',
          pink: '#ec4899',
          purple: '#a855f7',
          'purple-deep': '#9333ea',
          cyan: '#22d3ee',
          'cyan-deep': '#06b6d4',
        },

        // Typographic hierarchy tokens
        ink: {
          DEFAULT: '#fafafa',
          secondary: '#d4d4d8',
          muted: '#a1a1aa',
          subtle: '#71717a',
          faint: '#52525b',
        },

        // Semantic accent palette
        accent: {
          warm: '#fbbf24',
          success: '#10b981',
          danger: '#ef4444',
          info: '#38bdf8',
        },
      },
      fontFamily: {
        sans: [
          '"Plus Jakarta Sans"',
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'sans-serif',
        ],
        display: [
          '"Plus Jakarta Sans"',
          'ui-sans-serif',
          'system-ui',
          'sans-serif',
        ],
      },
      fontSize: {
        // Type scale aligned to design tokens
        'display-2xl': ['4.5rem', { lineHeight: '1', letterSpacing: '-0.04em', fontWeight: '800' }],
        'display-xl': ['3.75rem', { lineHeight: '1.05', letterSpacing: '-0.035em', fontWeight: '800' }],
        'display-lg': ['3rem', { lineHeight: '1.1', letterSpacing: '-0.03em', fontWeight: '800' }],
        'h1': ['2.25rem', { lineHeight: '1.15', letterSpacing: '-0.025em', fontWeight: '700' }],
        'h2': ['1.875rem', { lineHeight: '1.2', letterSpacing: '-0.02em', fontWeight: '700' }],
        'h3': ['1.5rem', { lineHeight: '1.3', letterSpacing: '-0.015em', fontWeight: '700' }],
        'h4': ['1.25rem', { lineHeight: '1.35', letterSpacing: '-0.01em', fontWeight: '600' }],
      },
      borderRadius: {
        // Aligned to design tokens
        'sm': '0.5rem',
        'md': '0.75rem',
        'lg': '1rem',
        'xl': '1.25rem',
        '2xl': '1.5rem',
      },
      transitionTimingFunction: {
        // Watchfy signature curves
        'exo-out': 'cubic-bezier(0.16, 1, 0.3, 1)',
        'exo-in': 'cubic-bezier(0.7, 0, 0.84, 0)',
        'spring': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
      },
      transitionDuration: {
        '180': '180ms',
        '300': '300ms',
        '500': '500ms',
        '1000': '1000ms',
      },
      boxShadow: {
        '1': '0 1px 2px rgba(0, 0, 0, 0.4)',
        '2': '0 4px 16px rgba(0, 0, 0, 0.45)',
        '3': '0 12px 32px rgba(0, 0, 0, 0.55)',
        '4': '0 25px 60px -15px rgba(0, 0, 0, 0.8)',
        'glow-red': '0 8px 32px -8px rgba(239, 68, 68, 0.4)',
        'glow-purple': '0 8px 32px -8px rgba(168, 85, 247, 0.35)',
        'glow-brand': '0 8px 32px -8px rgba(236, 72, 153, 0.35)',
      },
      maxWidth: {
        'content': '1440px',
      },
      keyframes: {
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'fade-up': {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'scale-in': {
          from: { opacity: '0', transform: 'scale(0.96)' },
          to: { opacity: '1', transform: 'scale(1)' },
        },
        'pulse-glow': {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.55', transform: 'scale(0.92)' },
        },
      },
      animation: {
        'fade-in': 'fade-in var(--duration-base, 300ms) var(--ease-exo-out, cubic-bezier(0.16, 1, 0.3, 1)) both',
        'fade-up': 'fade-up var(--duration-slow, 500ms) var(--ease-exo-out, cubic-bezier(0.16, 1, 0.3, 1)) both',
        'scale-in': 'scale-in var(--duration-base, 300ms) var(--ease-exo-out, cubic-bezier(0.16, 1, 0.3, 1)) both',
        'pulse-glow': 'pulse-glow 1.6s var(--ease-standard, cubic-bezier(0.4, 0, 0.2, 1)) infinite',
      },
      zIndex: {
        'nav': '50',
        'modal': '80',
        'toast': '90',
        'tooltip': '100',
      },
    },
  },
  plugins: [
    // Native custom scrollbar styling for horizontal scrolling media rows
    function ({ addUtilities }) {
      addUtilities({
        '.no-scrollbar': {
          '-ms-overflow-style': 'none',
          'scrollbar-width': 'none',
          '&::-webkit-scrollbar': {
            display: 'none',
          },
        },
        '.premium-scrollbar': {
          '&::-webkit-scrollbar': {
            width: '6px',
            height: '6px',
          },
          '&::-webkit-scrollbar-track': {
            background: '#070b14',
          },
          '&::-webkit-scrollbar-thumb': {
            background: '#1e293b',
            borderRadius: '9999px',
          },
          '&::-webkit-scrollbar-thumb:hover': {
            background: '#a855f7',
          },
        },
      });
    },
  ],
};
