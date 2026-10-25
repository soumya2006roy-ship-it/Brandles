import { buildOgImage } from "@/app/og-image";

export const alt = "BrandLens: compare campaign assets with approved brand evidence";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function Image() {
  return buildOgImage("Catch campaign conflicts before approval.", "Campaign review with approved evidence");
}
