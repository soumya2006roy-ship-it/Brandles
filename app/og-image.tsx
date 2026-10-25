import { ImageResponse } from "next/og";

export function buildOgImage(title: string, eyebrow: string) {
  return new ImageResponse(
    <div style={{ display: "flex", width: "100%", height: "100%", padding: "64px 74px", flexDirection: "column", justifyContent: "space-between", color: "#17231e", background: "#f7f5ef", fontFamily: "sans-serif" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "14px", fontSize: 24, fontWeight: 700, letterSpacing: "-1px" }}><div style={{ display: "flex", width: 40, height: 40, alignItems: "center", justifyContent: "center", borderRadius: 8, color: "#f7f5ef", background: "#17231e", fontSize: 29 }}>B<span style={{ color: "#ef805e" }}>.</span></div>brandlens</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 18, maxWidth: 930 }}><div style={{ color: "#c04b2b", fontSize: 17, fontWeight: 700, letterSpacing: "3px", textTransform: "uppercase" }}>{eyebrow}</div><div style={{ fontSize: 65, fontWeight: 600, letterSpacing: "-3px", lineHeight: 1.04 }}>{title}</div></div>
      <div style={{ display: "flex", justifyContent: "space-between", paddingTop: 20, borderTop: "1px solid #d9ddd4", color: "#66716a", fontSize: 16 }}><span>Approved sources · Campaign assets · Reviewer approval</span><span>BrandLens</span></div>
    </div>,
    { width: 1200, height: 630 },
  );
}
