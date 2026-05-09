import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        cream: "#FFF7E8",
        surface: "#FFFFFF",
        skySoft: "#EAF6FF",
        ink: "#24313A",
        muted: "#6B7C89",
        borderSoft: "#E8DDC8",
        pistachio: "#B8D979",
        pistachioDark: "#8FB45A",
        orange: "#F79A3E",
        coral: "#F2634A",
        blueSoft: "#8FC4E8",
        yellowStar: "#FFD36A",
      },
      boxShadow: {
        panel: "0 20px 40px rgba(36, 49, 58, 0.08)",
      },
    },
  },
  plugins: [],
};

export default config;
