/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(214 32% 91%)",
        background: "hsl(210 40% 98%)",
        foreground: "hsl(222 47% 11%)",
        muted: "hsl(215 16% 47%)",
        panel: "hsl(0 0% 100%)",
        primary: "hsl(170 76% 28%)",
        primaryDark: "hsl(174 84% 18%)",
        accent: "hsl(39 92% 54%)",
      },
      boxShadow: {
        soft: "0 16px 50px -30px rgb(15 23 42 / 0.35)",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
