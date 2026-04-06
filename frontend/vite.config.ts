/// <reference types="vitest/config" />
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { visualizer } from 'rollup-plugin-visualizer';

const apiTarget =
  process.env.VITE_API_PROXY_TARGET
  ?? process.env.VITE_API_BASE_URL
  ?? 'http://127.0.0.1:5000';

const enableBundleAnalysis = process.env.ANALYZE_BUNDLE === 'true';

export default defineConfig({
  plugins: [
    react(),
    enableBundleAnalysis
      ? visualizer({
          template: 'treemap',
          gzipSize: true,
          brotliSize: true,
          filename: 'dist/stats.html',
          open: true,
        })
      : undefined,
  ],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    include: ['src/**/*.test.{ts,tsx}'],
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return;
          if (id.includes('react') || id.includes('scheduler')) return 'vendor-react';
          if (id.includes('framer-motion')) return 'vendor-motion';
          if (id.includes('three')) return 'vendor-three';
          if (id.includes('lucide-react')) return 'vendor-icons';
          if (id.includes('@radix-ui')) return 'vendor-radix';
          if (id.includes('jspdf-autotable')) return 'vendor-autotable';
          if (id.includes('jspdf')) return 'vendor-jspdf';
          if (id.includes('html2canvas')) return 'vendor-html2canvas';
          if (id.includes('dompurify')) return 'vendor-dompurify';
          if (id.includes('lenis')) return 'vendor-lenis';
          if (id.includes('i18next')) return 'vendor-i18n';
          if (id.includes('@stripe')) return 'vendor-stripe';
          if (id.includes('@supabase')) return 'vendor-supabase';
          if (id.includes('@react-spring')) return 'vendor-spring';
          return 'vendor';
        },
      },
    },
    // Enable CSS code splitting
    cssCodeSplit: true,
    // Generate source maps for production debugging
    sourcemap: false,
    // Chunk size warning limit (500KB)
    chunkSizeWarningLimit: 500,
    // Minify with terser-like options (default esbuild is fine too)
    minify: 'esbuild',
    // Target modern browsers for smaller bundles
    target: 'es2020',
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    allowedHosts: ['.emergentagent.com', '.preview.emergentagent.com'],
    proxy: {
      '/api': { target: apiTarget, changeOrigin: true },
      '/health': { target: apiTarget, changeOrigin: true },
    }
  },
  // Optimize dependencies pre-bundling
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-dom/client',
      'react-router-dom',
      'framer-motion',
      'lucide-react',
    ],
    // Exclude heavy deps from pre-bundling (they'll be lazy-loaded)
    exclude: ['three', '@react-spring/web'],
  },
});
