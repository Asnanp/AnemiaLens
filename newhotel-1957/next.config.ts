import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  serverExternalPackages: ["@prisma/client"],
  // Standalone output for optimized Docker / self-hosted prod builds (pairs with Dockerfile)
  output: "standalone",
  // Performance budgets (informational; CI/build + Vercel Analytics enforce/monitor):
  // - First Load JS (main bundles): target < 180 kB gzipped for 10k-scale mobile users
  // - Total JS: < 500 kB
  // - Image optimization via Next + public/ images
  // Review: after `npm run build` check .next/static/chunks ; use `npm run perf:budget`
  // + Vercel Speed Insights / Web Vitals for runtime LCP/FID/CLS budgets.
  experimental: {
    // serverActions already stable in 15
  },
  // Image loading perf + layered edge: optimize all public/*.jpg menu photos (unique for 1957), long cache, modern formats.
  // Pairs with fetchPriority/lazy in MenuClient + admin + waiter for LCP wins on menu loads (<100ms target).
  images: {
    formats: ["image/avif", "image/webp"],
    minimumCacheTTL: 60 * 60 * 24 * 30, // 30 days for static dish photos (rarely change)
    deviceSizes: [64, 84, 180, 400, 640, 828],
    imageSizes: [16, 32, 48, 96],
    dangerouslyAllowSVG: false,
  },
  // Extra edge cache headers for menu (Vercel CDN) — augments per-route Cache-Control. Heavy logic (AI) stays dynamic.
  async headers() {
    return [
      {
        source: "/api/menu(.*)",
        headers: [{ key: "Cache-Control", value: "public, s-maxage=300, stale-while-revalidate=1800" }],
      },
      {
        source: "/api/categories",
        headers: [{ key: "Cache-Control", value: "public, s-maxage=300, stale-while-revalidate=900" }],
      },
    ];
  },
};

export default nextConfig;