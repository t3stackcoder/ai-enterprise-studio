/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'bg-default': '#1F1F1F',
        'bg-paper': '#2D2D30',
        'text-primary': '#FFFFFF',
        'text-secondary': '#F0F0F0',
        'divider': '#404040',
        'icon-primary': '#E0E0E0',
        'grey-900': '#1F1F1F',
        primary: {
          main: 'oklch(0.63 0.1699 149.21)',
          hover: 'oklch(0.68 0.14 149.21)',
        },
      },
    },
  },
  plugins: [],
}

