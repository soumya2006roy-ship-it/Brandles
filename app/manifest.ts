import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "BrandLens — brand governance for every channel",
    short_name: "BrandLens",
    description: "An AI-assisted, source-based campaign review concept.",
    start_url: "/",
    display: "standalone",
    background_color: "#f7f5ef",
    theme_color: "#17231e",
    icons: [
      { src: "/favicon.ico", sizes: "48x48", type: "image/x-icon" },
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
      { src: "/maskable-icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
