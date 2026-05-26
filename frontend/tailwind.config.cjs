/** @type {import('tailwindcss').Config} */
export default {
  // Broadened to explicitly capture Svelte, Qwik, and standard Astro layouts
  content: [
    './src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Premium Dark Slate System
        surface: '#0f1724',
        'surface-raised': '#1a2332',
        'surface-sunken': '#070b14',
        border: '#1e293b',
        
        // Typography Hierarchy Tokens
        text: '#ffffff',
        'text-secondary': '#cbd5e1',
        'text-muted': '#94a3b8',
        
        // Brand Identity Vectors (Deep Violet & Vibrant Electric Cyan)
        primary: '#8b5cf6',
        'primary-hover': '#7c3aed',
        secondary: '#22d3ee',
        'secondary-hover': '#06b6d4',
      },
      // Added a matching layout transition preset for your card hovering animations
      transitionTimingFunction: {
        'exo-out': 'cubic-bezier(0.16, 1, 0.3, 1)',
      }
    },
  },
  plugins: [
    // Adds native custom scrollbar styling hooks for your horizontal scrolling media rows
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
            background: '#070b14', // surface-sunken
          },
          '&::-webkit-scrollbar-thumb': {
            background: '#1e293b', // border
            borderRadius: '9999px',
          },
          '&::-webkit-scrollbar-thumb:hover': {
            background: '#8b5cf6', // primary
          },
        },
      });
    },
  ],
};