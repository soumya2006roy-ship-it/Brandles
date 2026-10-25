import { notFound } from "next/navigation";
import { buildOgImage } from "@/app/og-image";
import { siteConfig } from "@/site.config";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const page = siteConfig.pages[slug as keyof typeof siteConfig.pages];
  if (!page || slug === "features") notFound();
  return buildOgImage(page.title, page.eyebrow);
}
