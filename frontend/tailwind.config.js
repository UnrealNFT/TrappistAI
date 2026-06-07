/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#00ff41',
          dark: '#00cc33',
          light: '#33ff66'
        },
        secondary: {
          DEFAULT: '#00ff41',
          dark: '#009922',
          light: '#66ff88'
        },
        success: '#00ff41',
        danger: '#ff0000',
        warning: '#ffff00',
        dark: {
          bg: '#000000',
          card: '#0a0a0a',
          hover: '#0f0f0f',
          border: '#00ff41'
        }
      },
      fontFamily: {
        sans: ['Courier New', 'monospace'],
        mono: ['Courier New', 'monospace']
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.5s ease-out',
        'scale-in': 'scaleIn 0.3s ease-out',
        'spin-slow': 'spin 3s linear infinite',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'scan': 'scan 7.5s linear infinite',
        'blink': 'blink 500ms linear infinite',
        'glow': 'glow 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' }
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' }
        },
        scaleIn: {
          '0%': { transform: 'scale(0.9)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' }
        },
        scan: {
          '0%': { backgroundPosition: '0 -100vh' },
          '35%, 100%': { backgroundPosition: '0 100vh' }
        },
        blink: {
          '0%, 49%': { opacity: '0' },
          '50%, 100%': { opacity: '1' }
        },
        glow: {
          '0%, 100%': { textShadow: '0 0 10px #00ff41, 0 0 20px #00ff41' },
          '50%': { textShadow: '0 0 20px #00ff41, 0 0 30px #00ff41, 0 0 40px #00ff41' }
        }
      },
      screens: {
        'xs': '475px',
        '3xl': '1920px'
      }
    },
  },
  plugins: [],
}
