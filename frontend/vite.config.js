/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const dirname = typeof __dirname !== 'undefined' ? __dirname : path.dirname(fileURLToPath(import.meta.url));
// More info at: https://storybook.js.org/docs/next/writing-tests/integrations/vitest-addon
const apiTarget = process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:5000';
export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
        proxy: {
            '/api': apiTarget,
            '/health': apiTarget
        }
    }
});
