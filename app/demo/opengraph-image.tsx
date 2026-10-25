import { buildOgImage } from "@/app/og-image";

export const alt = "BrandLens guided skincare campaign simulation";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function Image() {
  return buildOgImage("Review the campaign before it goes live.", "Seeded local simulation");
}
