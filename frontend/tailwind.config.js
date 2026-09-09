/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"IBM Plex Sans Arabic"', "Tahoma", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
      },
      colors: {
        brand: {
          50: "#EEF5FE",
          100: "#DCEBFD",
          200: "#B4D6FA",
          300: "#7CB8F5",
          400: "#3F93EC",
          500: "#1A76DC",
          600: "#0969DA",
          700: "#0B54AE",
          800: "#0E458A",
          900: "#0F3A70",
        },
        ink: "#0D1117",
      },
    },
  },
  plugins: [],
};
