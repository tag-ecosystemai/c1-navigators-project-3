/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f0f7ff",
          100: "#e0effe",
          200: "#bae0fd",
          300: "#7cc5fb",
          400: "#36a7f7",
          500: "#0c8ce9",
          600: "#026fc7",
          700: "#0359a1",
          800: "#074c84",
          900: "#0c406e",
          950: "#082849",
        },
        navy: {
          800: "#0d1b2a",
          850: "#0b1726",
          900: "#07111f",
          950: "#040b14",
        },
        slate: {
          750: "#243447",
          850: "#162235",
        }
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
