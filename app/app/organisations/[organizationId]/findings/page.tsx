"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiRequest } from "@/app/lib/api-client";

type Finding = { id: string; campaign_id: string; campaign_name: string; asset_id: string | null; finding_type: string; severity: string; status: string; flagged_region: Record<string, unknown> | null; source_title: string | null; source_version: number | null; source_page_number: number | null; source_location_label: string | null; source_text: string | null; quoted_excerpt: string | null; confidence: number | null; suggested_fix: string | null };

export default function FindingsPage({ params }: { params: Promise<{ organizationId: string }> }) {
  const [orgId, setOrgId] = useState("");
  const [rows, setRows] = useState<Finding[]>([]);
  const [status, setStatus] = useState("open");
  const [severity, setSeverity] = useState("");
  const [channel, setChannel] = useState("");
  const [query, setQuery] = useState("");
  const [applied, setApplied] = useState("");
  const [offset, setOffset] = useState(0);
  const [loadedQuery, setLoadedQuery] = useState("");
  const [error, setError] = useState("");
  const requestQuery = new URLSearchParams({ offset: String(offset), limit: "25", ...(status ? { status } : {}), ...(severity ? { severity } : {}), ...(channel ? { channel } : {}), ...(applied ? { search: applied } : {}) }).toString();
  const loading = !orgId || loadedQuery !== `${orgId}?${requestQuery}`;
  useEffect(() => { void params.then(({ organizationId }) => setOrgId(organizationId)); }, [params]);
  useEffect(() => {
    if (!orgId) return;
    let active = true;
    const key = `${orgId}?${requestQuery}`;
    apiRequest<Finding[]>(`orgs/${orgId}/findings?${requestQuery}`).then((result) => { if (active) { setRows(result); setError(""); } }).catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "Could not load findings."); }).finally(() => { if (active) setLoadedQuery(key); });
    return () => { active = false; };
  }, [orgId, requestQuery]);
  function submit(event: React.FormEvent<HTMLFormElement>) { event.preventDefault(); setOffset(0); setApplied(query.trim()); }
  return <>
    <header className="workspace-heading"><p className="eyebrow"><Link href={`/app/organisations/${orgId}`}>Workspace</Link> / Campaign findings</p><h1>Findings</h1><p>Open a finding to inspect its evidence map, source version and passage location.</p></header>
    <section className="workspace-section"><form className="finding-filters" onSubmit={submit}><label className="form-field">Search<input value={query} onChange={(event) => setQuery(event.target.value)} maxLength={100} placeholder="Campaign or finding type"/></label><label className="form-field">Status<select value={status} onChange={(event) => { setStatus(event.target.value); setOffset(0); }}><option value="open">Open</option><option value="clarification_requested">Clarification requested</option><option value="resolved">Resolved</option><option value="dismissed">Dismissed</option><option value="">All statuses</option></select></label><label className="form-field">Severity<select value={severity} onChange={(event) => { setSeverity(event.target.value); setOffset(0); }}><option value="">All severities</option><option>critical</option><option>high</option><option>medium</option><option>low</option></select></label><label className="form-field">Channel<input value={channel} onChange={(event) => { setChannel(event.target.value); setOffset(0); }} maxLength={50} placeholder="Instagram"/></label><button className="small-button" type="submit">Search</button></form>
      {error && <p className="auth-message auth-error" role="alert">{error}</p>}{loading ? <div className="workspace-skeleton" aria-label="Loading findings"><div/><div/><div/></div> : rows.length === 0 ? <div className="workspace-empty"><h2>No findings match</h2><p>Try another filter or run a scan on a campaign.</p></div> : <ul className="finding-list">{rows.map((finding) => <li key={finding.id}><details><summary><span className={`status-label status-${finding.severity}`}>{finding.severity}</span> {finding.finding_type.replaceAll("_", " ")} · {finding.campaign_name} · {finding.status.replaceAll("_", " ")}</summary><div className="finding-evidence"><p><strong>Flagged text</strong><br/>{finding.quoted_excerpt ?? "No quoted passage"}</p><p><strong>Suggested fix</strong><br/>{finding.suggested_fix ?? "Needs human verification"}</p>{finding.source_text ? <blockquote>{finding.source_text}<small>{finding.source_title} · v{finding.source_version ?? "?"} · {finding.source_page_number ? `page ${finding.source_page_number}` : finding.source_location_label ?? "passage"}</small></blockquote> : <p>No approved source passage is linked to this finding.</p>}<Link className="text-link" href={`/app/organisations/${orgId}/campaigns/${finding.campaign_id}`}>Open campaign</Link></div></details></li>)}</ul>}
      <div className="inline-actions"><button className="small-button" disabled={offset === 0 || loading} onClick={() => setOffset(Math.max(0, offset - 25))}>Previous</button><span>Page {Math.floor(offset / 25) + 1}</span><button className="small-button" disabled={loading || rows.length < 25} onClick={() => setOffset(offset + 25)}>Next</button></div>
    </section>
  </>;
}
