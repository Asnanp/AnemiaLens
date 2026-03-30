import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        background: '#0B0B0F',
        surface: '#12121A',
        surfaceHover: '#1A1A24',
        brand: {
          blue: '#3B82F6',
          teal: '#14B8A6',
          purple: '#8B5CF6',
          dark: '#05050A',
        },
        accent: {
          primary: '#6366F1',
          glow: 'rgba(99, 102, 241, 0.45)',
          teal: '#2DD4BF',
        },
        glass: {
          light: 'rgba(255, 255, 255, 0.05)',
          medium: 'rgba(255, 255, 255, 0.08)',
          high: 'rgba(255, 255, 255, 0.12)',
        },
        text: {
          primary: '#F8FAFC',
          secondary: '#94A3B8',
          muted: '#64748B',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow-pulse': 'glow-pulse 3s ease-in-out infinite alternate',
        'float': 'float 6s ease-in-out infinite',
      },
      keyframes: {
        'glow-pulse': {
          '0%': { boxShadow: '0 0 10px rgba(99, 102, 241, 0.2), 0 0 20px rgba(99, 102, 241, 0.1)' },
          '100%': { boxShadow: '0 0 25px rgba(99, 102, 241, 0.5), 0 0 50px rgba(99, 102, 241, 0.2)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        }
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'mesh-light': 'linear-gradient(to right, #1f2937 1px, transparent 1px), linear-gradient(to bottom, #1f2937 1px, transparent 1px)',
        'mesh-dark': 'linear-gradient(to right, rgba(255,255,255,0.05) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.05) 1px, transparent 1px)',
      },
      backdropBlur: {
        xs: '2px',
        glass: '16px',
      }
    },
  },
  plugins: [],
};

export default config;
