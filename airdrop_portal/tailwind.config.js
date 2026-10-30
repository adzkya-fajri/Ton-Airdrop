/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        obsidian: {
          950: '#060609',
          900: '#09090e',
          850: '#0e0e17',
          800: '#141422',
          700: '#1e1e30',
        },
        amethyst: {
          DEFAULT: '#8b5cf6',
          hover: '#7c3aed',
          glow: 'rgba(139, 92, 246, 0.25)',
        },
        ton: {
          DEFAULT: '#0098ea',
          dark: '#007ab8',
        }
      }
    },
  },
  plugins: [],
}
