import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { siteConfig, type ContentPageSlug } from "@/site.config";
import { Breadcrumbs, RelatedReading } from "@/app/ui";
import { BreadcrumbJsonLd, JsonLd } from "@/app/structured-data";

export function generateStaticParams() {
  return Object.keys(siteConfig.pages).filter((slug) => slug !== "features").map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const page = siteConfig.pages[slug as ContentPageSlug];
  if (!page) return {};
  const canonical = `/${slug}`;
  return {
    title: page.eyebrow,
    description: page.description,
    alternates: { canonical },
    openGraph: { type: "article", title: page.title, description: page.description, url: canonical },
    twitter: { card: "summary_large_image", title: page.title, description: page.description },
  };
}

export default async function ContentPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const page = siteConfig.pages[slug as ContentPageSlug];
  if (!page || slug === "features") notFound();
  const crumbs = [{ name: "Home", path: "/" }, { name: page.eyebrow, path: `/${slug}` }];
  const contactSchema = slug === "contact" ? { "@context": "https://schema.org", "@type": "ContactPage", name: page.title, description: page.description, url: new URL(`/${slug}`, siteConfig.url).toString(), about: { "@id": `${siteConfig.url}/#organization` } } : null;
  const faqSchema = slug === "how-it-works" ? { "@context": "https://schema.org", "@type": "FAQPage", mainEntity: siteConfig.faqs.map((faq) => ({ "@type": "Question", name: faq.question, acceptedAnswer: { "@type": "Answer", text: faq.answer } })) } : null;
  return <main className="page-main"><div className="wrap page-wrap"><BreadcrumbJsonLd items={crumbs}/>{contactSchema && <JsonLd data={contactSchema}/ >}{faqSchema && <JsonLd data={faqSchema}/>}<Breadcrumbs current={page.eyebrow} /><header className="page-hero"><p className="eyebrow">{page.eyebrow}</p><h1>{page.title}</h1><p className="page-intro">{page.intro}</p></header>{slug === "campaign-consistency-graph" && <div className="page-graph"><CampaignGraph /></div>}<div className="content-sections">{page.sections.map((section) => <section className="content-section" key={section.title}><div className="content-rule"/><div><h2>{section.title}</h2><p>{section.body}</p></div></section>)}{slug === "how-it-works" && <section className="faq-section"><p className="eyebrow">Common questions</p><h2>What BrandLens does, clearly.</h2>{siteConfig.faqs.map((faq) => <details key={faq.question}><summary>{faq.question}</summary><p>{faq.answer}</p></details>)}</section>}</div>{slug === "how-it-works" && <div className="inline-cta"><p>See the workflow using the seeded skincare scenario.</p><Link className="button button-primary" href="/demo">Open demo <span aria-hidden="true">↗</span></Link></div>}<RelatedReading slugs={page.related} /></div></main>;
}

import { CampaignGraph } from "@/app/ui";
