/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border) / <alpha-value>)",
        background: "hsl(var(--background) / <alpha-value>)",
        foreground: "hsl(var(--foreground) / <alpha-value>)",
        muted: "hsl(var(--muted) / <alpha-value>)",
        panel: "hsl(var(--panel) / <alpha-value>)",
        panelRaised: "hsl(var(--panel-raised) / <alpha-value>)",
        sidebar: "hsl(var(--sidebar) / <alpha-value>)",
        primary: "hsl(var(--primary) / <alpha-value>)",
        primaryDark: "hsl(var(--primary-dark) / <alpha-value>)",
        accent: "hsl(var(--accent) / <alpha-value>)",
      },
      boxShadow: {
        soft: "0 18px 40px -28px hsl(var(--shadow) / 0.4)",
        panel: "0 12px 32px -22px hsl(var(--shadow) / 0.42)",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
