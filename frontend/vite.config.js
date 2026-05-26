/// <reference types="vitest/config" />
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { visualizer } from 'rollup-plugin-visualizer';
import fs from 'fs';
import path from 'path';
function loadEnvFile() {
    const envPath = path.resolve(process.cwd(), '.env');
    if (fs.existsSync(envPath)) {
        const content = fs.readFileSync(envPath, 'utf-8');
        content.split('\n').forEach(line => {
            const match = line.match(/^\s*([\w.-]+)\s*=\s*(.*)?\s*$/);
            if (match) {
                const key = match[1];
                let value = (match[2] || '').trim();
                if (value.startsWith('"') && value.endsWith('"'))
                    value = value.slice(1, -1);
                if (value.startsWith("'") && value.endsWith("'"))
                    value = value.slice(1, -1);
                // Do not overwrite variables already set in process.env (like from webServer.env)
                if (!process.env[key]) {
                    process.env[key] = value;
                }
            }
        });
    }
}
loadEnvFile();
const apiTarget = process.env.VITE_API_PROXY_TARGET
    ?? process.env.VITE_API_BASE_URL
    ?? 'http://127.0.0.1:8000';
const enableBundleAnalysis = process.env.ANALYZE_BUNDLE === 'true';
const allowedHosts = process.env.VITE_ALLOWED_HOSTS
    ? process.env.VITE_ALLOWED_HOSTS.split(',').map((host) => host.trim()).filter(Boolean)
    : undefined;
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
                    if (!id.includes('node_modules'))
                        return;
                    if (id.includes('react')
                        || id.includes('scheduler')
                        || id.includes('react-router')
                        || id.includes('@remix-run')) {
                        return 'vendor-react';
                    }
                    if (id.includes('framer-motion'))
                        return 'vendor-motion';
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
                    if (id.includes('lenis'))
                        return 'vendor-lenis';
                    if (id.includes('i18next'))
                        return 'vendor-i18n';
                    if (id.includes('@stripe'))
                        return 'vendor-stripe';
                    return undefined;
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
        host: process.env.VITE_DEV_HOST ?? '127.0.0.1',
        port: Number(process.env.VITE_PORT ?? 3000),
        strictPort: true,
        allowedHosts,
        proxy: {
            '/api': { target: apiTarget, changeOrigin: true },
            '/health': { target: apiTarget, changeOrigin: true },
            '/readyz': { target: apiTarget, changeOrigin: true },
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
        exclude: [],
    },
});
