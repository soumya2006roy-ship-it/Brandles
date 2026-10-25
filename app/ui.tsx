"use client";

import Link from "next/link";
import Image from "next/image";
import { createContext, useContext, useEffect, useSyncExternalStore, useState } from "react";
import { siteConfig } from "@/site.config";

type ToastMessage = { id: number; message: string; kind: "success" | "error" | "info" };
type ToastContextValue = { notify: (message: string, kind?: ToastMessage["kind"]) => void };
const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [messages, setMessages] = useState<ToastMessage[]>([]);
  function notify(message: string, kind: ToastMessage["kind"] = "info") {
    const id = Date.now() + Math.random();
    setMessages((current) => [...current, { id, message, kind }]);
    window.setTimeout(() => setMessages((current) => current.filter((toast) => toast.id !== id)), 4200);
  }
  return <ToastContext.Provider value={{ notify }}>{children}<div className="toast-region" aria-live="polite" aria-atomic="false">{messages.map((toast) => <div className={`toast toast-${toast.kind}`} key={toast.id} role={toast.kind === "error" ? "alert" : "status"}><span>{toast.message}</span><button type="button" onClick={() => setMessages((current) => current.filter((item) => item.id !== toast.id))} aria-label="Dismiss notification">×</button></div>)}</div></ToastContext.Provider>;
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used within ToastProvider");
  return context.notify;
}

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
  return <header className="site-header"><div className="wrap header-inner"><Link href="/" className="brand" aria-label="BrandLens home"><Image className="brand-icon" src="/icon-192.png" width={32} height={32} alt=""/><span>brandlens</span></Link><nav className="desktop-nav" aria-label="Main navigation">{siteConfig.navigation.map((item) => <Link href={item.href} key={item.href}>{item.label}</Link>)}</nav><div className="header-actions"><ThemeToggle /><Link className="header-cta" href="/demo">View demo <span aria-hidden="true">↗</span></Link></div><details className="mobile-nav"><summary aria-label="Open navigation menu"><span /><span /><span /></summary><nav aria-label="Mobile navigation">{siteConfig.navigation.map((item) => <Link href={item.href} key={item.href}>{item.label}</Link>)}<Link href="/demo">View demo</Link></nav></details></div></header>;
}

export function SiteFooter() {
  return <footer className="site-footer"><div className="wrap footer-main"><div><Link href="/" className="brand footer-brand"><Image className="brand-icon" src="/icon-192.png" width={32} height={32} alt=""/><span>brandlens</span></Link><p>{siteConfig.tagline}</p><p className="footer-disclaimer">AI-assisted review. People keep the judgement.</p></div><nav className="footer-links" aria-label="Footer navigation">{siteConfig.footerLinks.map((item) => <Link href={item.href} key={item.href}>{item.label}</Link>)}</nav></div><div className="wrap footer-bottom"><span>BrandLens · campaign review concept</span><span>Evidence-backed flags. Human approval.</span></div></footer>;
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
