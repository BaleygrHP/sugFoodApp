import type { NextConfig } from "next";

/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.unsplash.com",
      },
    ],
  },
  // Turbopack config for Next.js 16
  turbopack: {},
};

module.exports = nextConfig;


export default nextConfig;
