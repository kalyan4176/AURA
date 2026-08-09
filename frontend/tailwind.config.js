/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#F7F9FC", // Off White background
        card: "#FFFFFF", // White card
        border: "#E2E8F0", // Light Gray border
        primary: {
          DEFAULT: "#1E3A5F", // Deep Navy primary
          hover: "#142A45",
        },
        secondary: {
          DEFAULT: "#4F6D8A", // Slate Blue secondary
          hover: "#3C546C",
        },
        accent: {
          DEFAULT: "#2F855A", // Emerald accent
          hover: "#226343",
        },
        text: {
          primary: "#1A202C", // Charcoal text
          secondary: "#4A5568", // Slate Gray text
          muted: "#718096", // Gray muted text
        },
        info: "#3182CE", // Blue info
        warning: "#D69E2E", // Amber warning
        error: "#C53030", // Crimson error
        success: "#2F855A", // Emerald success
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
