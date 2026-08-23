/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        chart: {
          navy: "#12192B",
          navyLight: "#1B2440",
          parchment: "#EDE6D6",
          parchmentDim: "#B9B2A0",
          brass: "#C08A3E",
          brassLight: "#D9A860",
        },
        difficulty: {
          easy: "#5B7A5C",
          moderate: "#C08A3E",
          hard: "#8B4A3A",
        },
      },
      fontFamily: {
        display: ["Fraunces", "serif"],
        body: ["Inter", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};