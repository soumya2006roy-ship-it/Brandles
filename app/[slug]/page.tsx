import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { siteConfig, type ContentPageSlug } from "@/site.config";
import { Breadcrumbs, RelatedReading } from "@/app/ui";

export function generateStaticParams() {
  return Object.keys(siteConfig.pages).filter((slug) => slug !== "features").map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const page = siteConfig.pages[slug as ContentPageSlug];
  return page ? { title: page.eyebrow, description: page.description } : {};
}

export default async function ContentPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const page = siteConfig.pages[slug as ContentPageSlug];
  if (!page || slug === "features") notFound();
  return <main className="page-main"><div className="wrap page-wrap"><Breadcrumbs current={page.eyebrow} /><header className="page-hero"><p className="eyebrow">{page.eyebrow}</p><h1>{page.title}</h1><p className="page-intro">{page.intro}</p></header>{slug === "campaign-consistency-graph" && <div className="page-graph"><CampaignGraph /></div>}{slug === "features" && null}<div className="content-sections">{page.sections.map((section) => <section className="content-section" key={section.title}><div className="content-rule"/><div><h2>{section.title}</h2><p>{section.body}</p></div></section>)}</div>{slug === "how-it-works" && <div className="inline-cta"><p>See the workflow using the seeded skincare scenario.</p><Link className="button button-primary" href="/demo">Open demo <span aria-hidden="true">↗</span></Link></div>}<RelatedReading slugs={page.related} /></div></main>;
}

import { CampaignGraph } from "@/app/ui";
