"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest } from "@/app/lib/api-client";

type Dashboard = { pending_reviews: number; open_findings: number; recent_campaigns: { id: string; name: string; status: string; created_at: string }[]; expiring_offers: { rule_id: string; rule_type: string; offer_name: string | null; expires_at: string; source_title: string; source_version: number }[] };

export function OrganisationDashboard({ organizationId }: { organizationId: string }) {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => { const timer = window.setTimeout(() => { apiRequest<Dashboard>(`orgs/${organizationId}/dashboard`).then(setData).catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "Could not load workspace activity.")).finally(() => setLoading(false)); }, 0); return () => window.clearTimeout(timer); }, [organizationId]);

  if (loading) return <section className="workspace-section"><p className="eyebrow">Workspace dashboard</p><div className="workspace-skeleton" aria-label="Loading workspace dashboard"><div/><div/><div/></div></section>;
  if (error) return <section className="workspace-section"><p className="auth-message auth-error" role="alert">{error}</p></section>;
  if (!data) return <section className="workspace-empty"><h2>Workspace summary is unavailable</h2></section>;
  return <section className="workspace-section"><p className="eyebrow">Workspace dashboard · live workspace data</p><h2>Current work</h2><div className="dashboard-metrics"><Link href={`/app/organisations/${organizationId}/reviews`}><span>Pending reviews</span><strong>{data.pending_reviews}</strong></Link><Link href={`/app/organisations/${organizationId}/findings`}><span>Open findings</span><strong>{data.open_findings}</strong></Link><Link href={`/app/organisations/${organizationId}/campaigns`}><span>Recent campaigns</span><strong>{data.recent_campaigns.length}</strong></Link><div><span>Offers expiring within 30 days</span><strong>{data.expiring_offers.length}</strong></div></div>
    <div className="dashboard-panels"><div><h3>Recent campaigns</h3>{data.recent_campaigns.length ? <ul className="invite-list">{data.recent_campaigns.map((campaign) => <li key={campaign.id}><Link href={`/app/organisations/${organizationId}/campaigns/${campaign.id}`}><strong>{campaign.name}</strong><span>{campaign.status.replaceAll("_", " ")} · {new Date(campaign.created_at).toLocaleDateString()}</span></Link></li>)}</ul> : <div className="workspace-empty"><p>No campaigns have been created.</p><Link className="text-link" href={`/app/organisations/${organizationId}/campaigns`}>Create a campaign</Link></div>}</div><div><h3>Expiring offers</h3>{data.expiring_offers.length ? <ul className="invite-list">{data.expiring_offers.map((offer) => <li key={offer.rule_id}><div><strong>{offer.offer_name ?? offer.rule_type.replaceAll("_", " ")}</strong><span>{offer.source_title} v{offer.source_version} · expires {new Date(`${offer.expires_at}T00:00:00`).toLocaleDateString()}</span></div></li>)}</ul> : <div className="workspace-empty"><p>No approved offers expire in the next 30 days.</p></div>}</div></div>
  </section>;
}
