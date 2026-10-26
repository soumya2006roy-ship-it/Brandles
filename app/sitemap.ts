import type { MetadataRoute } from "next";
import { siteConfig } from "@/site.config";

export default function sitemap(): MetadataRoute.Sitemap {
  const paths = ["", "/problem", "/how-it-works", "/campaign-consistency-graph", "/features", "/roles", "/security", "/roadmap", "/contact", "/privacy", "/cookies"];
  return paths.map((path) => ({ url: new URL(path, siteConfig.url).toString(), changeFrequency: path === "" ? "weekly" : "monthly", priority: path === "" ? 1 : 0.7 }));
}
