/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
const apiTarget = process.env.VITE_API_PROXY_TARGET
    ?? process.env.VITE_API_BASE_URL
    ?? 'https://asnannp-anemialens.hf.space';
export default defineConfig({
    plugins: [react()],
    build: {
        rollupOptions: {
            output: {
                manualChunks(id) {
                    if (!id.includes('node_modules'))
                        return;
                    if (id.includes('react') || id.includes('scheduler'))
                        return 'vendor-react';
                    if (id.includes('framer-motion'))
                        return 'vendor-motion';
                    if (id.includes('three'))
                        return 'vendor-three';
                    if (id.includes('lucide-react'))
                        return 'vendor-icons';
                    if (id.includes('@radix-ui'))
                        return 'vendor-radix';
                    if (id.includes('jspdf-autotable'))
                        return 'vendor-autotable';
                    if (id.includes('jspdf'))
                        return 'vendor-jspdf';
                    if (id.includes('html2canvas'))
                        return 'vendor-html2canvas';
                    if (id.includes('dompurify'))
                        return 'vendor-dompurify';
                    return 'vendor';
                },
            },
        },
    },
    server: {
        host: '0.0.0.0',
        port: 3000,
        proxy: {
            '/api': { target: apiTarget, changeOrigin: true },
            '/health': { target: apiTarget, changeOrigin: true },
        }
    }
});
