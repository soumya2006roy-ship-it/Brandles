"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { apiRequest, type User } from "@/app/lib/api-client";

export function ProductShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiRequest<User>("auth/me").then(setUser).catch(() => router.replace("/login")).finally(() => setLoading(false));
  }, [router]);

  async function signOut() {
    try { await apiRequest<void>("auth/logout", { method: "POST" }); } finally { router.replace("/login"); router.refresh(); }
  }

  if (loading) return <main className="product-loading" aria-live="polite"><p className="eyebrow">BrandLens workspace</p><h1>Checking your session</h1><div className="loading-rule"/></main>;
  if (!user) return <main className="product-loading"><p>Opening sign in…</p></main>;

  return <div className="product-frame">
    <a className="skip-link" href="#workspace-main">Skip to workspace</a>
    <header className="product-header"><Link className="product-brand" href="/app">BrandLens <span>Workspace</span></Link><nav aria-label="Workspace navigation"><Link aria-current={pathname === "/app" ? "page" : undefined} href="/app">Overview</Link><Link aria-current={pathname.startsWith("/app/admin") ? "page" : undefined} href="/app/admin/verifications">Verification queue</Link><Link aria-current={pathname.startsWith("/app/account") ? "page" : undefined} href="/app/account/sessions">Sessions</Link><Link aria-current={pathname.startsWith("/app/security") ? "page" : undefined} href="/app/security">Security</Link><Link href="/invite">Redeem invite</Link></nav><div className="product-user"><span>{user.display_name}</span><button type="button" onClick={signOut}>Sign out</button></div></header>
    <main id="workspace-main" className="product-main">{children}</main>
    <footer className="product-footer"><span>BrandLens workspace</span><Link href="/privacy">Privacy information</Link><Link href="/security">Security overview</Link></footer>
  </div>;
}
