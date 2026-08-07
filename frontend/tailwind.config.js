/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0b0f19", // sleek dark blue-grey background
        card: "rgba(17, 24, 39, 0.7)", // glass card fill
        border: "rgba(255, 255, 255, 0.08)", // glass border
        primary: {
          DEFAULT: "#10b981", // vibrant emerald
          hover: "#059669",
        },
        secondary: {
          DEFAULT: "#6366f1", // royal indigo
          hover: "#4f46e5",
        },
        accent: "#f59e0b", // clean amber outlier warning
        text: {
          primary: "#f3f4f6", // off white text
          secondary: "#9ca3af", // gray text
        }
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
      },
      backdropBlur: {
        xs: "2px",
      }
    },
  },
  plugins: [],
}
