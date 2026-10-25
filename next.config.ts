import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Keep generated output separate from OneDrive's synced .next placeholder on Windows.
  distDir: ".next-build",
  poweredByHeader: false,
  images: { formats: ["image/avif", "image/webp"] },
  async headers() {
    const headers = [
      // MIME sniffing can turn a harmless upload into executable content.
      { key: "X-Content-Type-Options", value: "nosniff" },
      // Prevent framing in browsers that do not support CSP frame-ancestors.
      { key: "X-Frame-Options", value: "DENY" },
      // Avoid leaking full page URLs to unrelated sites.
      { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
      // This site needs no camera, microphone, location, payment, or USB access.
      { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()" },
      // Keep cross-origin documents from sharing the top-level browsing context.
      { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
    ];
    if (process.env.NODE_ENV === "production") {
      // Enforce HTTPS for this host and its subdomains in production.
      headers.push({ key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" });
    }
    return [{ source: "/:path*", headers }];
  },
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
