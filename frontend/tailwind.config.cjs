/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,ts,tsx}', './src/**/*.svelte'],
  theme: {
    extend: {
      colors: {
        surface: '#0f1724',
        'surface-raised': '#1a2332',
        'surface-sunken': '#070b14',
        border: '#1e293b',
        text: '#ffffff',
        'text-secondary': '#cbd5e1',
        'text-muted': '#94a3b8',
        primary: '#8b5cf6',
        'primary-hover': '#7c3aed',
        secondary: '#22d3ee',
        'secondary-hover': '#06b6d4',
      },
    },
  },
  plugins: [],
};