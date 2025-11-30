import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable standalone output for Docker deployment
  output: "standalone",
  // Exclude problematic server packages from bundling
  serverExternalPackages: ["pino", "pino-pretty", "thread-stream"],
};

export default nextConfig;
