import type { NextConfig } from "next";

// output "standalone": the build (done on GitHub Actions, never on the VPS) produces a small
// self-contained server.js that the VPS runs with plain Node (~150 MB RAM).
const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
};

export default nextConfig;
