import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow the dev server to serve its client JS / HMR to browsers hitting it via
  // a LAN IP (not just localhost). Without this, Next.js 16 blocks /_next/* dev
  // resources cross-origin, the page never hydrates, and forms native-submit.
  allowedDevOrigins: [
    "172.16.2.9",
    "172.16.2.*",
    "172.16.*",
    "192.168.*",
    "10.*",
  ],
};

export default nextConfig;
