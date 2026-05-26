/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,ts,tsx}', './src/**/*.svelte'],
  theme: {
    extend: {
      colors: {
        surface: '#1a1a1a',
        'surface-raised': '#262626',
        'surface-sunken': '#111111',
        border: '#333333',
        text: '#ffffff',
        'text-muted': '#a1a1aa',
      },
    },
  },
  plugins: [],
};