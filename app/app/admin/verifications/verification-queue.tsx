"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { ApiError, apiRequest, type Organization, type VerificationHistory } from "@/app/lib/api-client";

type VerificationDecision = "approved" | "rejected" | "more_information_required";

export function VerificationQueue() {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [histories, setHistories] = useState<Record<string, VerificationHistory[]>>({});
  const [error, setError] = useState("");
  const [forbidden, setForbidden] = useState(false);
  const [loading, setLoading] = useState(true);
  const [queueView, setQueueView] = useState<"pending" | "awaiting_info">("pending");
  const [decisions, setDecisions] = useState<Record<string, VerificationDecision>>({});

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    setForbidden(false);
    try {
      const queue = await apiRequest<Organization[]>(`platform/verifications?status=${queueView}`);
      setOrganizations(queue);
      const historyRows = await Promise.all(queue.map(async (org) => [org.id, await apiRequest<VerificationHistory[]>(`platform/verifications/${org.id}/history`)] as const));
      setHistories(Object.fromEntries(historyRows));
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 403) setForbidden(true);
      else setError(cause instanceof Error ? cause.message : "Could not load the verification queue.");
    } finally { setLoading(false); }
  }, [queueView]);

  useEffect(() => {
    const timer = window.setTimeout(() => { void load(); }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  async function decide(event: FormEvent<HTMLFormElement>, organizationId: string) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const decision = String(form.get("decision")) as VerificationDecision;
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
    <div className="inline-actions" role="group" aria-label="Organisation approval queue">
      <button className="small-button" type="button" aria-pressed={queueView === "pending"} onClick={() => setQueueView("pending")}>Pending review</button>
      <button className="small-button" type="button" aria-pressed={queueView === "awaiting_info"} onClick={() => setQueueView("awaiting_info")}>Awaiting info</button>
    </div>
    <p className="field-help">{queueView === "pending" ? `${organizations.length} pending organisation${organizations.length === 1 ? "" : "s"}` : `${organizations.length} organisation${organizations.length === 1 ? "" : "s"} awaiting creator information`}</p>
    {organizations.length === 0 ? <section className="workspace-empty"><h2>{queueView === "pending" ? "No organisations are waiting for review" : "No organisations are awaiting information"}</h2><p>{queueView === "pending" ? "New and resubmitted organisations appear in this queue." : "Organisations will appear here after an admin requests more information."}</p></section> : <div className="verification-list">{organizations.map((org) => { const latest = org.submissions[org.submissions.length - 1]; const decision = decisions[org.id] ?? "approved"; const noteRequired = decision === "rejected" || decision === "more_information_required"; return <article className="verification-item" key={org.id}><div><p className="eyebrow">{org.industry} · {new Date(org.created_at).toLocaleString()}</p><h2>{org.name}</h2><dl><div><dt>Official email</dt><dd>{org.official_email}</dd></div><div><dt>Website</dt><dd><a href={org.website} target="_blank" rel="noopener noreferrer">{org.website}</a></dd></div><div><dt>Contact person</dt><dd>{org.contact_person}</dd></div></dl>{latest?.note && <p><strong>Creator note:</strong> {latest.note}</p>}</div>{queueView === "pending" ? <form className="verification-decision" onSubmit={(event) => decide(event, org.id)}><label className="form-field">Decision<select name="decision" value={decision} onChange={(event) => setDecisions((current) => ({ ...current, [org.id]: event.target.value as VerificationDecision }))}><option value="approved">Approve organisation</option><option value="more_information_required">Request more information</option><option value="rejected">Reject organisation</option></select></label><label className="form-field">Decision note<textarea name="note" maxLength={1200} required={noteRequired} placeholder={noteRequired ? "Add a note explaining this decision" : "Optional for approval"}/></label><button className="button button-primary" type="submit">Record decision</button></form> : <p className="workspace-notice">Waiting for the organisation creator to respond.</p>}<details className="verification-history"><summary>Submission documents and notes</summary>{org.submissions.length ? <ol>{org.submissions.map((submission) => <li key={submission.id}><strong>{submission.submitted_by_name} · {new Date(submission.created_at).toLocaleString()}</strong>{submission.note && <p>Creator note: {submission.note}</p>}{submission.original_filename ? <p><a href={`/api/product/platform/verifications/${org.id}/submissions/${submission.id}/document`}>View / download {submission.original_filename} ({(submission.size_bytes / 1048576).toFixed(2)} MB)</a></p> : <p>No document submitted</p>}</li>)}</ol> : <p>No submissions have been recorded.</p>}</details><details className="verification-history"><summary>Decision history</summary>{histories[org.id]?.length ? <ol>{histories[org.id].map((entry) => <li key={entry.id}><strong>{entry.decision.replaceAll("_", " ")}</strong><span>{entry.actor_name} · {new Date(entry.created_at).toLocaleString()}</span>{entry.note && <p>{entry.note}</p>}</li>)}</ol> : <p>No decisions have been recorded.</p>}</details></article>; })}</div>}
  </>;
}
