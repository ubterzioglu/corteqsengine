/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#002FA7',
          hover: '#00227A',
        },
        accent: {
          red: '#FF3B30',
          yellow: '#FFCC00',
        },
        surface: {
          DEFAULT: '#FFFFFF',
          secondary: '#FAFAFA',
        },
        border: {
          subtle: '#E4E4E7',
          focus: '#002FA7',
        }
      },
      fontFamily: {
        display: ['Cabinet Grotesk', 'sans-serif'],
        body: ['IBM Plex Sans', 'sans-serif'],
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'slide-in': 'slideIn 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideIn: {
          '0%': { transform: 'translateX(-10px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
