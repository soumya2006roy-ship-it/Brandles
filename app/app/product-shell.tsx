"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";
import { apiRequest, type User } from "@/app/lib/api-client";
import { ThemeToggle } from "@/app/ui";
import { LanguageSelect, useLocale } from "@/app/i18n";

type NavigationItem = { label: string; href: string; match: string };

export function ProductShell({ children }: { children: ReactNode }) {
  const { t } = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const routeOrganizationId = pathname.match(/^\/app\/organisations\/([^/]+)/)?.[1];
  const organizationId = routeOrganizationId === "new" ? undefined : routeOrganizationId;

  useEffect(() => {
    let active = true;
    apiRequest<User>("auth/me")
      .then((currentUser) => { if (active) setUser(currentUser); })
      .catch(() => { if (active) router.replace("/login"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [router]);

  async function signOut() {
    try { await apiRequest<void>("auth/logout", { method: "POST" }); }
    finally { router.replace("/login"); router.refresh(); }
  }

  const organizationNavigation: NavigationItem[] = organizationId ? [
    { label: t("nav.overview"), href: `/app/organisations/${organizationId}`, match: `/app/organisations/${organizationId}` },
    { label: t("nav.campaigns"), href: `/app/organisations/${organizationId}/campaigns`, match: `/app/organisations/${organizationId}/campaigns` },
    { label: t("nav.health"), href: `/app/organisations/${organizationId}/campaign-health`, match: `/app/organisations/${organizationId}/campaign-health` },
    { label: t("nav.findings"), href: `/app/organisations/${organizationId}/findings`, match: `/app/organisations/${organizationId}/findings` },
    { label: t("nav.reviews"), href: `/app/organisations/${organizationId}/reviews`, match: `/app/organisations/${organizationId}/reviews` },
    { label: t("nav.sources"), href: `/app/organisations/${organizationId}/sources`, match: `/app/organisations/${organizationId}/sources` },
    { label: t("nav.rules"), href: `/app/organisations/${organizationId}/rules`, match: `/app/organisations/${organizationId}/rules` },
    { label: t("nav.team"), href: `/app/organisations/${organizationId}#team`, match: "#never-active" },
    { label: t("nav.settings"), href: `/app/organisations/${organizationId}#settings`, match: "#never-active" },
    { label: t("nav.audit"), href: `/app/organisations/${organizationId}/audit`, match: `/app/organisations/${organizationId}/audit` },
  ] : [];
  const accountNavigation: NavigationItem[] = [
    { label: t("nav.organisations"), href: "/app", match: "/app" },
    { label: t("nav.verification"), href: "/app/admin/verifications", match: "/app/admin" },
    { label: t("nav.sessions"), href: "/app/account/sessions", match: "/app/account" },
    { label: t("nav.security"), href: "/app/security", match: "/app/security" },
    { label: t("nav.join"), href: "/app/invite", match: "/app/invite" },
  ];

  if (loading) return <main className="product-loading" aria-live="polite"><p className="eyebrow">BrandLens workspace</p><h1>Checking your session</h1><div className="loading-rule"/></main>;
  if (!user) return <main className="product-loading"><p>Opening sign in…</p></main>;

  const navigation = organizationId ? organizationNavigation : accountNavigation;
  return <div className="product-frame">
    <a className="skip-link" href="#workspace-main">{t("nav.skip")}</a>
    <header className="product-header">
      <Link className="product-brand" href="/app" aria-label="BrandLens workspace home">
        <Image className="product-brand-mark" src="/icon-192.png" width={48} height={48} alt="" priority/>
        <span className="product-brand-copy">BrandLens<small>Workspace</small></span>
      </Link>
      <div className="product-header-actions">
        <span className="product-user-name">{user.display_name}</span>
        <LanguageSelect/>
        <ThemeToggle/>
        <button className="product-signout" type="button" onClick={signOut}>{t("nav.signOut")}</button>
      </div>
    </header>
    <div className="product-layout">
      <aside className="product-sidebar" aria-label="Workspace menu">
        {organizationId && <div className="sidebar-context"><span className="sidebar-context-mark" aria-hidden="true">W</span><span><small>{t("nav.currentWorkspace")}</small><strong>Organisation</strong></span></div>}
        <p className="sidebar-label">{organizationId ? "WORKSPACE" : "YOUR ACCOUNT"}</p>
        <nav className="product-nav" aria-label={organizationId ? "Organisation navigation" : "Account navigation"}>
          {navigation.map((item) => {
            const active = item.match !== "#never-active" && (pathname === item.match || (item.match !== "/app" && pathname.startsWith(`${item.match}/`)));
            return <Link key={item.label} href={item.href} aria-current={active ? "page" : undefined} className={active ? "product-nav-link is-active" : "product-nav-link"}><span className="product-nav-indicator" aria-hidden="true"/>{item.label}</Link>;
          })}
        </nav>
        {organizationId && <Link className="sidebar-back-link" href="/app">{t("nav.allOrganisations")}</Link>}
        <div className="sidebar-note"><span className="sidebar-note-dot" aria-hidden="true"/><span><strong>Evidence first</strong><small>Checks are grounded in approved sources.</small></span></div>
      </aside>
      <div className="product-content-column">
        <main id="workspace-main" className="product-main">{children}</main>
        <footer className="product-footer"><span>BrandLens workspace</span><Link href="/privacy">Privacy information</Link><Link href="/security">Security overview</Link></footer>
      </div>
    </div>
  </div>;
}
