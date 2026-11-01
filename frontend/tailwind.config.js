/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./features/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // NEPTUNE Design System Palette
        navy: {
          950: "#050810",
          900: "#0a0e1a",
          800: "#0d1220",
          700: "#111827",
          600: "#1a2234",
          500: "#1e293b",
        },
        charcoal: {
          900: "#121620",
          800: "#1a1f2e",
          700: "#232838",
          600: "#2d3345",
        },
        // Accent colors
        "electric-blue": "#00b4d8",
        "electric-blue-glow": "rgba(0, 180, 216, 0.2)",
        cyan: {
          DEFAULT: "#00f5d4",
          glow: "rgba(0, 245, 212, 0.2)",
          dim: "#00c9ac",
        },
        // Market colors
        bull: {
          DEFAULT: "#10b981",   // emerald
          bright: "#34d399",
          glow: "rgba(16, 185, 129, 0.2)",
        },
        bear: {
          DEFAULT: "#ef4444",   // crimson
          bright: "#f87171",
          glow: "rgba(239, 68, 68, 0.2)",
        },
        // Status
        gold: "#f59e0b",
        purple: "#818cf8",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
        display: ["Outfit", "Inter", "sans-serif"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "fade-in": "fadeIn 0.2s ease-out",
        "slide-up": "slideUp 0.3s ease-out",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      backdropBlur: {
        xs: "2px",
      },
    },
  },
  plugins: [],
};
