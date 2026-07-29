import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: { "50": "#f0fdf4", "500": "#22c55e", "600": "#16a34a", "700": "#15803d" },
      },
    },
  },
  plugins: [],
};

export default config;
