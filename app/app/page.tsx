"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest, type OrganizationSummary } from "@/app/lib/api-client";

export default function WorkspacePage() {
  const [organizations, setOrganizations] = useState<OrganizationSummary[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    apiRequest<OrganizationSummary[]>("orgs").then(setOrganizations).catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "Could not load organisations.")).finally(() => setLoading(false));
  }, []);

  return <>
    <header className="workspace-heading"><p className="eyebrow">Your workspaces</p><h1>Organisations</h1><p>Each workspace holds its own members, approved sources and campaign reviews.</p><Link className="button button-primary" href="/app/organisations/new">Create organisation</Link></header>
    {error && <p className="auth-message auth-error" role="alert">{error}</p>}
    {loading ? <div className="workspace-skeleton" aria-label="Loading organisations"><div/><div/><div/></div> : organizations.length === 0 ? <section className="workspace-empty"><h2>Start with an organisation</h2><p>Submit an organisation for verification. A platform administrator must approve it before you can invite members or add workspace material.</p><Link className="text-link" href="/app/organisations/new">Enter organisation details</Link></section> : <div className="organization-list">{organizations.map((org) => <Link className="organization-row" href={`/app/organisations/${org.id}`} key={org.id}><span><strong>{org.name}</strong><small>{org.industry} · {org.role}</small></span><span className={`status-label status-${org.verification_status}`}>{org.verification_status.replaceAll("_", " ")}</span></Link>)}</div>}
    <section className="workspace-scope"><p className="eyebrow">Product scope</p><p>Approved sources, rules, campaign assets, deterministic scans and reviewer records are available. Model judgement needs a configured provider; no live AI provider is connected in this build.</p></section>
  </>;
}
