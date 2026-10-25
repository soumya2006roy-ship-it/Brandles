import type { Metadata } from "next";
import { Breadcrumbs, RelatedReading } from "@/app/ui";
import { siteConfig } from "@/site.config";

export const metadata: Metadata = { title: siteConfig.pages.features.title, description: siteConfig.pages.features.description };

export default function FeaturesPage() {
  return <main className="page-main"><div className="wrap page-wrap"><Breadcrumbs current="Seven innovations"/><header className="page-hero"><p className="eyebrow">{siteConfig.pages.features.eyebrow}</p><h1>{siteConfig.pages.features.title}</h1><p className="page-intro">{siteConfig.pages.features.intro}</p></header><div className="innovation-grid">{siteConfig.innovations.map((feature, index) => <article className="innovation-card" id={feature.id} key={feature.id}><div className="innovation-card-top"><span>0{index + 1}</span><span className="feature-status">{feature.status}</span></div><h2>{feature.title}</h2><p>{feature.summary}</p><div className="innovation-demo"><span>DEMO</span>{feature.demo}</div></article>)}</div><p className="prototype-callout">The English/Hindi checker and Instagram/LinkedIn previews are simple rule-based prototypes. They are not perfect translation or exact platform rendering.</p><RelatedReading slugs={siteConfig.pages.features.related}/></div></main>;
}
