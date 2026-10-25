"use client";

import Link from "next/link";
import { useEffect, useSyncExternalStore } from "react";
import { siteConfig } from "@/site.config";

export function ThemeToggle() {
  const dark = useSyncExternalStore(
    (callback) => {
      window.addEventListener("brandlens-theme-change", callback);
      window.addEventListener("storage", callback);
      return () => {
        window.removeEventListener("brandlens-theme-change", callback);
        window.removeEventListener("storage", callback);
      };
    },
    () => document.documentElement.dataset.theme === "dark",
    () => false,
  );
  useEffect(() => {
    const saved = localStorage.getItem("brandlens-theme");
    const enabled = saved ? saved === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.dataset.theme = enabled ? "dark" : "light";
    window.dispatchEvent(new Event("brandlens-theme-change"));
  }, []);
  function toggle() {
    const next = !dark;
    document.documentElement.dataset.theme = next ? "dark" : "light";
    localStorage.setItem("brandlens-theme", next ? "dark" : "light");
    window.dispatchEvent(new Event("brandlens-theme-change"));
  }
  return <button className="theme-toggle" type="button" onClick={toggle} aria-label={`Switch to ${dark ? "light" : "dark"} mode`} title="Toggle color theme">{dark ? "☼" : "◐"}</button>;
}

export function SiteHeader() {
  return <header className="site-header"><div className="wrap header-inner"><Link href="/" className="brand" aria-label="BrandLens home"><span className="brand-mark">B<span>.</span></span><span>brandlens</span></Link><nav className="desktop-nav" aria-label="Main navigation">{siteConfig.navigation.map((item) => <Link href={item.href} key={item.href}>{item.label}</Link>)}</nav><div className="header-actions"><ThemeToggle /><Link className="header-cta" href="/demo">View demo <span aria-hidden="true">↗</span></Link></div><details className="mobile-nav"><summary aria-label="Open navigation menu"><span /><span /><span /></summary><nav aria-label="Mobile navigation">{siteConfig.navigation.map((item) => <Link href={item.href} key={item.href}>{item.label}</Link>)}<Link href="/demo">View demo</Link></nav></details></div></header>;
}

export function SiteFooter() {
  return <footer className="site-footer"><div className="wrap footer-main"><div><Link href="/" className="brand footer-brand"><span className="brand-mark">B<span>.</span></span><span>brandlens</span></Link><p>{siteConfig.tagline}</p><p className="footer-disclaimer">AI-assisted review. People keep the judgement.</p></div><nav className="footer-links" aria-label="Footer navigation">{siteConfig.footerLinks.map((item) => <Link href={item.href} key={item.href}>{item.label}</Link>)}</nav></div><div className="wrap footer-bottom"><span>BrandLens · campaign review concept</span><span>Evidence-backed flags. Human approval.</span></div></footer>;
}

export function CampaignGraph() {
  return <div className="graph-card"><div className="graph-top"><span className="graph-kicker">CONSISTENCY MAP</span><span className="graph-live"><i /> 1 conflict found</span></div><svg className="graph-svg" viewBox="0 0 560 330" role="img" aria-labelledby="graph-title graph-description"><title id="graph-title">Campaign Consistency Graph illustration</title><desc id="graph-description">Three campaign assets connect to an approved offer. One email discount conflicts with the approved 20 percent offer.</desc><defs><pattern id="dots" width="18" height="18" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="currentColor" opacity=".08" /></pattern></defs><rect width="560" height="330" fill="url(#dots)"/><path className="graph-line graph-line-approved" d="M96 76 C180 76 182 165 260 165"/><path className="graph-line graph-line-conflict" d="M464 76 C380 76 378 165 300 165"/><path className="graph-line graph-line-approved" d="M96 252 C180 252 182 165 260 165"/><path className="graph-line" d="M300 165 C370 165 376 252 464 252"/><g className="graph-node node-source"><rect x="18" y="42" width="158" height="68" rx="12"/><text x="34" y="69">APPROVED SOURCE</text><text x="34" y="91" className="node-value">Offer · 20% off</text></g><g className="graph-node node-asset"><rect x="384" y="42" width="158" height="68" rx="12"/><text x="400" y="69">EMAIL</text><text x="400" y="91" className="node-value">Offer · 30% off</text></g><g className="graph-node node-asset"><rect x="18" y="218" width="158" height="68" rx="12"/><text x="34" y="245">INSTAGRAM</text><text x="34" y="267" className="node-value">Claim · Hydration</text></g><g className="graph-node node-asset"><rect x="384" y="218" width="158" height="68" rx="12"/><text x="400" y="245">POSTER</text><text x="400" y="267" className="node-value">Logo · Previous</text></g><g className="graph-center"><circle cx="280" cy="165" r="42"/><circle className="orbit" cx="280" cy="165" r="53"/><text x="280" y="161" textAnchor="middle">CAMPAIGN</text><text x="280" y="178" textAnchor="middle" className="center-sub">3 assets</text></g><circle className="conflict-pulse" cx="398" cy="102" r="6"/></svg><div className="graph-legend"><span><i className="legend-source" /> approved source</span><span><i className="legend-conflict" /> mismatch</span><span><i className="legend-asset" /> campaign asset</span></div></div>;
}

export function Breadcrumbs({ current }: { current: string }) {
  return <nav aria-label="Breadcrumb" className="breadcrumbs"><ol><li><Link href="/">Home</Link></li><li aria-hidden="true">/</li><li aria-current="page">{current}</li></ol></nav>;
}

export function RelatedReading({ slugs }: { slugs: readonly string[] }) {
  const links = slugs.map((slug) => {
    if (slug === "demo") return { title: "Explore the guided demo", href: "/demo" };
    const page = siteConfig.pages[slug as keyof typeof siteConfig.pages];
    return page ? { title: page.eyebrow, href: `/${slug}` } : null;
  }).filter((link): link is { title: string; href: string } => Boolean(link));
  return <aside className="related-reading"><p className="eyebrow">Related reading</p><div>{links.map((link) => <Link key={link.href} href={link.href}>{link.title} <span aria-hidden="true">↗</span></Link>)}</div></aside>;
}
