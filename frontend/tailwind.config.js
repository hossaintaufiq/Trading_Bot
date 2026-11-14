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
        // Premium ink palette (deep, slightly violet-tinted neutrals).
        // Overriding slate re-skins every existing page consistently.
        slate: {
          50: "#f5f5fa",
          100: "#ececf4",
          200: "#d9d9e8",
          300: "#b9b9d0",
          400: "#8d8da9",
          500: "#6b6b88",
          600: "#4a4a63",
          700: "#2f2f45",
          800: "#1d1d2e",
          900: "#13131f",
          950: "#0a0a12",
        },
        navy: {
          950: "#07070d",
          900: "#0a0a12",
          800: "#0f0f1a",
          700: "#13131f",
          600: "#1a1a29",
          500: "#232336",
        },
        charcoal: {
          900: "#10101a",
          800: "#161622",
          700: "#1d1d2e",
          600: "#2a2a40",
        },
        // Single refined accent: iris (indigo → violet). Replaces cyan/blue everywhere.
        iris: {
          300: "#c4b5fd",
          400: "#a78bfa",
          500: "#8b7cf6",
          600: "#7461e8",
          700: "#5b4bc9",
        },
        cyan: {
          DEFAULT: "#a78bfa",
          glow: "rgba(167, 139, 250, 0.2)",
          dim: "#8b7cf6",
          300: "#c4b5fd",
          400: "#a78bfa",
          500: "#8b7cf6",
          600: "#7461e8",
          700: "#5b4bc9",
          800: "#44388f",
          900: "#2b2460",
          950: "#1a1640",
        },
        blue: {
          300: "#c4b5fd",
          400: "#a78bfa",
          500: "#8b7cf6",
          600: "#7461e8",
          700: "#5b4bc9",
          800: "#44388f",
          900: "#2b2460",
          950: "#1a1640",
        },
        "electric-blue": "#8b7cf6",
        bull: { DEFAULT: "#34d399", bright: "#6ee7b7", glow: "rgba(52,211,153,0.2)" },
        bear: { DEFAULT: "#fb7185", bright: "#fda4af", glow: "rgba(251,113,133,0.2)" },
        gold: "#e8c77d",
        purple: "#a78bfa",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "Inter", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "JetBrains Mono", "monospace"],
        display: ["var(--font-display)", "Outfit", "Inter", "sans-serif"],
      },
      boxShadow: {
        premium: "0 1px 0 0 rgba(255,255,255,0.05) inset, 0 12px 40px -12px rgba(0,0,0,0.6)",
        glow: "0 0 0 1px rgba(167,139,250,0.35), 0 8px 30px -8px rgba(139,124,246,0.45)",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "fade-in": "fadeIn 0.3s ease-out",
        "slide-up": "slideUp 0.4s cubic-bezier(0.22,1,0.36,1)",
      },
      keyframes: {
        fadeIn: { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      backdropBlur: { xs: "2px" },
    },
  },
  plugins: [],
};
