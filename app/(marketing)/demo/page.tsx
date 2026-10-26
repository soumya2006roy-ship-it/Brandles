import type { Metadata } from "next";
import Link from "next/link";
import { Breadcrumbs } from "@/app/ui";
import { BreadcrumbJsonLd } from "@/app/structured-data";
import { SampleWorkspace } from "@/app/(marketing)/demo/sample-workspace";

export const metadata: Metadata = { title: "Try the sample workspace", description: "Explore a read-only sample workspace with seeded campaign assets and evidence-linked findings.", alternates: { canonical: "/demo" } };

export default function DemoPage() {
  return <main className="page-main"><div className="wrap page-wrap"><BreadcrumbJsonLd items={[{ name: "Home", path: "/" }, { name: "Sample workspace", path: "/demo" }]}/><Breadcrumbs current="Sample workspace"/><header className="page-hero demo-page-hero"><p className="eyebrow">Read-only sample workspace</p><h1>Try the sample <em>workspace.</em></h1><p className="page-intro">Explore the proposal’s fictional skincare campaign using seeded records from the product API. Changes and external model calls are disabled.</p><p><Link className="text-link" href="/register">Create an organisation to start your own workspace</Link></p></header><SampleWorkspace/></div></main>;
}
