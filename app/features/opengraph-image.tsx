import { buildOgImage } from "@/app/og-image";

export const alt = "BrandLens seven campaign review innovations";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function Image() {
  return buildOgImage("Seven ideas that make the graph useful.", "Campaign review innovations");
}
