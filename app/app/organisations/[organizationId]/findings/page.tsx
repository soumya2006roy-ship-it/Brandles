"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiRequest } from "@/app/lib/api-client";
import { buildFindingQuery } from "@/app/lib/finding-filters";

type Finding = { id: string; campaign_id: string; campaign_name: string; asset_id: string | null; finding_type: string; severity: string; status: string; flagged_region: Record<string, unknown> | null; source_title: string | null; source_version: number | null; source_page_number: number | null; source_location_label: string | null; source_text: string | null; quoted_excerpt: string | null; confidence: number | null; suggested_fix: string | null };
type FindingsOverview = { campaigns: { campaign_id: string; campaign_name: string; channels: string[]; current_asset_count: number; latest_scan_status: string | null; latest_scan_at: string | null; latest_scan_finding_count: number; scan_is_current: boolean }[]; approved_source_count: number; active_rule_count: number };

export default function FindingsPage({ params }: { params: Promise<{ organizationId: string }> }) {
  const [orgId, setOrgId] = useState("");
  const [rows, setRows] = useState<Finding[]>([]);
  const [overview, setOverview] = useState<FindingsOverview | null>(null);
  const [status, setStatus] = useState("open");
  const [severity, setSeverity] = useState("");
  const [channel, setChannel] = useState("");
  const [query, setQuery] = useState("");
  const [applied, setApplied] = useState("");
  const [offset, setOffset] = useState(0);
  const [loadedQuery, setLoadedQuery] = useState("");
  const [error, setError] = useState("");
  const requestQuery = buildFindingQuery({ offset, limit: 25, status, severity, channel, search: applied });
  const loading = !orgId || loadedQuery !== `${orgId}?${requestQuery}`;
  useEffect(() => { void params.then(({ organizationId }) => setOrgId(organizationId)); }, [params]);
  useEffect(() => {
    if (!orgId) return;
    let active = true;
    const key = `${orgId}?${requestQuery}`;
    apiRequest<Finding[]>(`orgs/${orgId}/findings?${requestQuery}`).then((result) => { if (active) { setRows(result); setError(""); } }).catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "Could not load findings."); }).finally(() => { if (active) setLoadedQuery(key); });
    return () => { active = false; };
  }, [orgId, requestQuery]);
  useEffect(() => {
    if (!orgId) return;
    let active = true;
    apiRequest<FindingsOverview>(`orgs/${orgId}/findings/overview`).then((result) => { if (active) setOverview(result); }).catch(() => { if (active) setOverview(null); });
    return () => { active = false; };
  }, [orgId]);
  function submit(event: React.FormEvent<HTMLFormElement>) { event.preventDefault(); setOffset(0); setApplied(query.trim()); }
  return <>
    <header className="workspace-heading"><p className="eyebrow"><Link href={`/app/organisations/${orgId}`}>Workspace</Link> / Campaign findings</p><h1>Findings</h1><p>Open a finding to inspect its evidence map, source version and passage location.</p></header>
    <section className="workspace-section"><div className="findings-overview"><div><h2>Latest campaign scans</h2><p>Campaigns appear here with their latest scan result, including scans that found nothing.</p></div><Link className="small-button" href={`/app/organisations/${orgId}/campaigns`}>Campaigns</Link></div>
      {!overview ? <div className="workspace-skeleton" aria-label="Loading campaign scans"><div/><div/><div/></div> : overview.campaigns.length === 0 ? <div className="workspace-empty"><h2>No campaigns yet</h2><p>Create a campaign and add an asset to get started.</p><Link className="text-link" href={`/app/organisations/${orgId}/campaigns`}>Open campaigns</Link></div> : <ul className="campaign-scan-list">{overview.campaigns.map((campaign) => <li key={campaign.campaign_id}><div><strong>{campaign.campaign_name}</strong><p>{campaign.channels.join(" · ")} · {campaign.current_asset_count} current {campaign.current_asset_count === 1 ? "asset" : "assets"}</p></div><div className="campaign-scan-result"><span className={`status-label ${campaign.latest_scan_status === "completed" && campaign.scan_is_current ? "status-approved" : ""}`}>{campaign.latest_scan_status ? campaign.latest_scan_status.replaceAll("_", " ") : "Not scanned"}{campaign.latest_scan_status === "completed" && !campaign.scan_is_current ? " · outdated" : ""}</span><strong>{campaign.latest_scan_status === "completed" ? `${campaign.latest_scan_finding_count} ${campaign.latest_scan_finding_count === 1 ? "finding" : "findings"}` : campaign.current_asset_count ? "Ready to scan" : "Add an asset"}</strong>{campaign.latest_scan_at && <time dateTime={campaign.latest_scan_at}>{new Date(campaign.latest_scan_at).toLocaleString()}</time>}</div><Link className="small-button" href={`/app/organisations/${orgId}/campaigns/${campaign.campaign_id}`}>Open campaign</Link></li>)}</ul>}
      {overview && overview.campaigns.length > 0 && <p className="findings-setup-note">Checks use your approved sources and active rules ({overview.approved_source_count} approved sources · {overview.active_rule_count} active rules). A zero-finding scan means no configured check flagged the current assets; it is not a certification. <Link className="text-link" href={`/app/organisations/${orgId}/sources`}>Sources</Link> · <Link className="text-link" href={`/app/organisations/${orgId}/rules`}>Rules</Link></p>}
      <form className="finding-filters" onSubmit={submit}><label className="form-field">Search<input value={query} onChange={(event) => setQuery(event.target.value)} maxLength={100} placeholder="Campaign or finding type"/></label><label className="form-field">Status<select value={status} onChange={(event) => { setStatus(event.target.value); setOffset(0); }}><option value="open">Open</option><option value="clarification_requested">Clarification requested</option><option value="resolved">Resolved</option><option value="dismissed">Dismissed</option><option value="">All statuses</option></select></label><label className="form-field">Severity<select value={severity} onChange={(event) => { setSeverity(event.target.value); setOffset(0); }}><option value="">All severities</option><option>critical</option><option>high</option><option>medium</option><option>low</option></select></label><label className="form-field">Channel<input value={channel} onChange={(event) => { setChannel(event.target.value); setOffset(0); }} maxLength={50} placeholder="Instagram"/></label><button className="small-button" type="submit">Search</button></form>
      {error && <p className="auth-message auth-error" role="alert">{error}</p>}{loading ? <div className="workspace-skeleton" aria-label="Loading findings"><div/><div/><div/></div> : rows.length === 0 ? <div className="workspace-empty"><h2>{applied || severity || channel || (status && status !== "open") ? "No findings match these filters" : "No open findings"}</h2><p>{applied || severity || channel || (status && status !== "open") ? "Clear or change the filters to see findings from current scans." : overview?.active_rule_count === 0 ? "The latest scans have no findings. Add approved sources and active rules, add meaningful asset content, then scan again to check against your guidance." : "The latest current scans have not produced any open findings. Review the scan results above or run a new scan after changing assets or rules."}</p>{!overview?.campaigns.length && <Link className="text-link" href={`/app/organisations/${orgId}/campaigns`}>Create a campaign</Link>}</div> : <ul className="finding-list">{rows.map((finding) => <li key={finding.id}><details><summary><span className={`status-label status-${finding.severity}`}>{finding.severity}</span> {finding.finding_type.replaceAll("_", " ")} · {finding.campaign_name} · {finding.status.replaceAll("_", " ")}</summary><div className="finding-evidence"><p><strong>Flagged text</strong><br/>{finding.quoted_excerpt ?? "No quoted passage"}</p><p><strong>Suggested fix</strong><br/>{finding.suggested_fix ?? "Needs human verification"}</p>{finding.source_text ? <blockquote>{finding.source_text}<small>{finding.source_title} · v{finding.source_version ?? "?"} · {finding.source_page_number ? `page ${finding.source_page_number}` : finding.source_location_label ?? "passage"}</small></blockquote> : <p>No approved source passage is linked to this finding.</p>}<Link className="text-link" href={`/app/organisations/${orgId}/campaigns/${finding.campaign_id}`}>Open campaign</Link></div></details></li>)}</ul>}
      <div className="inline-actions"><button className="small-button" disabled={offset === 0 || loading} onClick={() => setOffset(Math.max(0, offset - 25))}>Previous</button><span>Page {Math.floor(offset / 25) + 1}</span><button className="small-button" disabled={loading || rows.length < 25} onClick={() => setOffset(offset + 25)}>Next</button></div>
    </section>
  </>;
}
