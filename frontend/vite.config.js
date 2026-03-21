/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const dirname = typeof __dirname !== 'undefined' ? __dirname : path.dirname(fileURLToPath(import.meta.url));

// Local dev defaults to the live Hugging Face backend unless you explicitly
// override it for a local FastAPI process.
const apiTarget =
    process.env.VITE_API_PROXY_TARGET
    ?? process.env.VITE_API_BASE_URL
    ?? 'https://asnanp1-anemialens.hf.space';

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
