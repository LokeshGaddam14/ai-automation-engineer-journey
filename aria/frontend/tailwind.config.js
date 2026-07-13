/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Brand palette
        brand: {
          50:  '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
        },
        // Dark surface palette
        surface: {
          50:  '#f8fafc',
          100: '#f1f5f9',
          900: '#0A0F1E',
          800: '#0D1526',
          700: '#111827',
          600: '#1a2235',
          500: '#1e2a3d',
          400: '#243047',
        },
        // Accent colors
        accent: {
          purple: '#a855f7',
          pink:   '#ec4899',
          cyan:   '#06b6d4',
          green:  '#10b981',
          orange: '#f59e0b',
          red:    '#ef4444',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      backdropBlur: {
        xs: '2px',
      },
      animation: {
        'fade-in':    'fadeIn 0.3s ease-in-out',
        'slide-in':   'slideIn 0.3s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'count-up':   'countUp 1s ease-out forwards',
      },
      keyframes: {
        fadeIn: {
          '0%':   { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideIn: {
          '0%':   { opacity: '0', transform: 'translateX(-12px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
      },
      boxShadow: {
        'glass':     '0 8px 32px rgba(0, 0, 0, 0.4)',
        'glass-lg':  '0 20px 60px rgba(0, 0, 0, 0.5)',
        'glow':      '0 0 20px rgba(99, 102, 241, 0.4)',
        'glow-sm':   '0 0 10px rgba(99, 102, 241, 0.3)',
      },
    },
  },
  plugins: [],
}
