import { siteConfig } from "@/site.config";
import { headers } from "next/headers";

export async function JsonLd({ data }: { data: Record<string, unknown> | Record<string, unknown>[] }) {
  const nonce = (await headers()).get("x-nonce") ?? undefined;
  const safe = JSON.stringify(data).replace(/</g, "\\u003c");
  return <script nonce={nonce} type="application/ld+json" dangerouslySetInnerHTML={{ __html: safe }} />;
}

export async function SiteStructuredData() {
  return <JsonLd data={{
    "@context": "https://schema.org",
    "@graph": [
      { "@type": "Organization", "@id": `${siteConfig.url}/#organization`, name: "BrandLens", url: siteConfig.url, description: siteConfig.description },
      { "@type": "WebSite", "@id": `${siteConfig.url}/#website`, name: "BrandLens", url: siteConfig.url, publisher: { "@id": `${siteConfig.url}/#organization` }, inLanguage: "en" },
      { "@type": "SoftwareApplication", "@id": `${siteConfig.url}/#software`, name: "BrandLens", applicationCategory: "BusinessApplication", operatingSystem: "Web", description: siteConfig.description, url: siteConfig.url, publisher: { "@id": `${siteConfig.url}/#organization` } },
    ],
  }} />;
}

export function BreadcrumbJsonLd({ items }: { items: readonly { name: string; path: string }[] }) {
  return <JsonLd data={{
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, index) => ({ "@type": "ListItem", position: index + 1, name: item.name, item: new URL(item.path, siteConfig.url).toString() })),
  }} />;
}
