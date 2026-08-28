/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "#0A0A0C",
          surface: "#141416",
          surfaceLight: "#1C1C1F",
          border: "#2A2A2E",
        },
        text: {
          primary: "#F5F5F7",
          secondary: "#98989F",
          tertiary: "#5C5C63",
        },
        accent: {
          DEFAULT: "#3B82F6",
          light: "#60A5FA",
          dim: "#1E3A6B",
        },
        tier: {
          easy: "#34D399",
          moderate: "#FBBF24",
          hard: "#F87171",
        },
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      letterSpacing: {
        tightest: "-0.04em",
      },
    },
  },
  plugins: [],
};