/** @type {import('next').NextConfig} */
const nextConfig = {
  // Standalone output produces a minimal server bundle for the Docker image
  // (see Dockerfile) instead of requiring the full node_modules tree at runtime.
  output: "standalone",
};

export default nextConfig;
