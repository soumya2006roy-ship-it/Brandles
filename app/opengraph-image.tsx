import { buildOgImage } from "@/app/og-image";

export const alt = "BrandLens , brand governance for every channel";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function Image() {
  return buildOgImage("One campaign. One source of truth.", "Brand governance, made reviewable");
}
