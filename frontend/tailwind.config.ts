import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          dark: '#08080A',
          charcoal: '#111114',
          crimson: '#C8102E',
          accent: '#E8294A',
        },
        glass: {
          low: 'rgba(255, 255, 255, 0.03)',
          mid: 'rgba(255, 255, 255, 0.06)',
          high: 'rgba(255, 255, 255, 0.1)',
        },
        text: {
          primary: '#F5F5F7',
          secondary: 'rgba(245, 245, 247, 0.65)',
          dim: 'rgba(245, 245, 247, 0.38)',
        }
      },
      fontFamily: {
        sans: ['Barlow', 'system-ui', 'sans-serif'],
        serif: ['Cormorant Garamond', 'Georgia', 'serif'],
        mono: ['IBM Plex Mono', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'float': 'float 6s ease-in-out infinite',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(200, 16, 46, 0.2), 0 0 20px rgba(200, 16, 46, 0.1)' },
          '100%': { boxShadow: '0 0 20px rgba(200, 16, 46, 0.5), 0 0 40px rgba(200, 16, 46, 0.2)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        }
      },
      backdropBlur: {
        xs: '2px',
      }
    },
  },
  plugins: [],
};

export default config;
