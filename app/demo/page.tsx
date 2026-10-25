import type { Metadata } from "next";
import { Breadcrumbs } from "@/app/ui";
import { BreadcrumbJsonLd } from "@/app/structured-data";
import { DemoLoader } from "@/app/demo/demo-loader";

export const metadata: Metadata = { title: "Guided demo", description: "Explore a local simulation of the BrandLens skincare campaign review workflow.", alternates: { canonical: "/demo" }, openGraph: { type: "article", title: "BrandLens guided demo", description: "Explore a local simulation of the BrandLens skincare campaign review workflow.", url: "/demo" }, twitter: { card: "summary_large_image", title: "BrandLens guided demo", description: "Explore a local simulation of the BrandLens skincare campaign review workflow." } };

export default function DemoPage() {
  return <main className="page-main"><div className="wrap page-wrap"><BreadcrumbJsonLd items={[{ name: "Home", path: "/" }, { name: "Guided demo", path: "/demo" }]}/><Breadcrumbs current="Guided demo"/><header className="page-hero demo-page-hero"><p className="eyebrow">Seeded local simulation</p><h1>Review the campaign <em>before it goes live.</em></h1><p className="page-intro">Explore the proposal’s imaginary skincare brand scenario. The scan uses seeded rules and sample evidence in this browser; it does not send content to an AI service or publish to a platform.</p></header><DemoLoader/></div></main>;
}
