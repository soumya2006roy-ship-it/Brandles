"use client";

import { FormEvent, useEffect, useState } from "react";
import { ApiError, apiRequest, type Organization, type VerificationHistory } from "@/app/lib/api-client";

export function VerificationQueue() {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [histories, setHistories] = useState<Record<string, VerificationHistory[]>>({});
  const [error, setError] = useState("");
  const [forbidden, setForbidden] = useState(false);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError("");
    setForbidden(false);
    try {
      const queue = await apiRequest<Organization[]>("platform/verifications");
      setOrganizations(queue);
      const historyRows = await Promise.all(queue.map(async (org) => [org.id, await apiRequest<VerificationHistory[]>(`platform/verifications/${org.id}/history`)] as const));
      setHistories(Object.fromEntries(historyRows));
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 403) setForbidden(true);
      else setError(cause instanceof Error ? cause.message : "Could not load the verification queue.");
    } finally { setLoading(false); }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => { void load(); }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  async function decide(event: FormEvent<HTMLFormElement>, organizationId: string) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const decision = String(form.get("decision"));
    const note = String(form.get("note") ?? "").trim();
    setError("");
    try {
      await apiRequest(`platform/verifications/${organizationId}/decision`, { method: "POST", body: JSON.stringify({ decision, note: note || null }) });
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not record this decision."); }
  }

  if (loading) return <div className="workspace-skeleton" aria-label="Loading verification requests"><div/><div/></div>;
  if (forbidden) return <section className="workspace-empty"><p className="eyebrow">Restricted area</p><h1>Platform administrator access required</h1><p>This role is assigned by an operator through the trusted server-side CLI. It cannot be granted from the browser.</p></section>;
  return <>
    <header className="workspace-heading"><p className="eyebrow">Platform operations</p><h1>Organisation verification</h1><p>Review each submission and record a decision with your identity and timestamp.</p></header>
    {error && <p className="auth-message auth-error" role="alert">{error}</p>}
    {organizations.length === 0 ? <section className="workspace-empty"><h2>No organisations are waiting</h2><p>Pending and information-requested organisations appear here.</p></section> : <div className="verification-list">{organizations.map((org) => <article className="verification-item" key={org.id}><div><p className="eyebrow">{org.industry} · {new Date(org.created_at).toLocaleString()}</p><h2>{org.name}</h2><dl><div><dt>Official email</dt><dd>{org.official_email}</dd></div><div><dt>Website</dt><dd><a href={org.website} target="_blank" rel="noopener noreferrer">{org.website}</a></dd></div><div><dt>Contact person</dt><dd>{org.contact_person}</dd></div></dl></div><form className="verification-decision" onSubmit={(event) => decide(event, org.id)}><label className="form-field">Decision<select name="decision" defaultValue="approved"><option value="approved">Approve organisation</option><option value="more_information_required">Request more information</option><option value="rejected">Reject organisation</option></select></label><label className="form-field">Decision note<textarea name="note" maxLength={1200} placeholder="Required for rejection or more information"/></label><button className="button button-primary" type="submit">Record decision</button></form><details className="verification-history"><summary>Decision history</summary>{histories[org.id]?.length ? <ol>{histories[org.id].map((entry) => <li key={entry.id}><strong>{entry.decision.replaceAll("_", " ")}</strong><span>{entry.actor_name} · {new Date(entry.created_at).toLocaleString()}</span>{entry.note && <p>{entry.note}</p>}</li>)}</ol> : <p>No decisions recorded.</p>}</details></article>)}</div>}
  </>;
}
