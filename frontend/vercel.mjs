const configuredOrigin = process.env.RENDER_API_ORIGIN;

if (!configuredOrigin) {
  throw new Error("Set RENDER_API_ORIGIN to the Render service's HTTPS origin.");
}

const api = new URL(configuredOrigin);
if (
  api.protocol !== "https:" ||
  !api.hostname.endsWith(".onrender.com") ||
  api.username || api.password || api.port ||
  api.pathname !== "/" || api.search || api.hash
) {
  throw new Error("RENDER_API_ORIGIN must be an HTTPS onrender.com origin with no path.");
}

export const config = {
  framework: "vite",
  outputDirectory: "dist",
  rewrites: [
    { source: "/api/:path*", destination: `${api.origin}/api/:path*` },
    { source: "/logs", destination: "/index.html" },
    { source: "/settings", destination: "/index.html" },
  ],
};
