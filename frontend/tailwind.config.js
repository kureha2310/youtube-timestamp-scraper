/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'selector',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Noto Sans JP', 'Inter', 'system-ui', 'sans-serif'],
        mincho: ['Shippori Mincho', 'serif'],
      },
      transitionTimingFunction: {
        'elegant': 'cubic-bezier(0.4, 0.4, 0, 1)',
      },
    },
  },
  plugins: [],
}
