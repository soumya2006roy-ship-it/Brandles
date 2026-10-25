import type { Metadata } from "next";
import { DemoExperience } from "@/app/demo/demo-experience";
import { Breadcrumbs } from "@/app/ui";

export const metadata: Metadata = { title: "Guided demo", description: "Explore a local simulation of the BrandLens skincare campaign review workflow." };

export default function DemoPage() {
  return <main className="page-main"><div className="wrap page-wrap"><Breadcrumbs current="Guided demo"/><header className="page-hero demo-page-hero"><p className="eyebrow">Seeded local simulation</p><h1>Review the campaign <em>before it goes live.</em></h1><p className="page-intro">Explore the proposal’s imaginary skincare brand scenario. The scan uses seeded rules and sample evidence in this browser; it does not send content to an AI service or publish to a platform.</p></header><DemoExperience/></div></main>;
}
