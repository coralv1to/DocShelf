import type { NextConfig } from "next";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // Chuyển tiếp mọi request /api/* sang FastAPI
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` }];
  },

  // Cho phép mở dev server qua tên miền ngrok (Phần 10)
  allowedDevOrigins: ["*.ngrok-free.app", "*.ngrok-free.dev", "*.ngrok.app"],

  experimental: {
    agentFeedback: true,
    // Upload + embedding trên laptop có thể mất hơn 30 giây (mặc định),
    // nên nới thời gian chờ của proxy lên 3 phút.
    proxyTimeout: 180_000,
  },

  // --- Phần do create-next-app tạo sẵn: GIỮ NGUYÊN ---
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
