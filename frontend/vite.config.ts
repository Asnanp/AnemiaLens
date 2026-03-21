/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const apiTarget =
  process.env.VITE_API_PROXY_TARGET
  ?? process.env.VITE_API_BASE_URL
  ?? 'https://asnannp-anemialens.hf.space';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: apiTarget, changeOrigin: true },
      '/health': { target: apiTarget, changeOrigin: true },
    }
  }
});
