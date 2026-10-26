"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { apiRequest } from "@/app/lib/api-client";

type ReviewItem = { id: string; submission_id: string; campaign_id: string; campaign_name: string; asset_id: string; asset_version: number; decision: string; submitted_by_user_id: string | null; reviewer_user_id: string | null; comment: string | null; created_at: string };
type Submission = { organizationId: string; campaignId: string; campaignName: string; submissionId: string; rows: ReviewItem[]; createdAt: string };

export function ReviewQueue({ organizationId }: { organizationId: string }) {
  const [rows, setRows] = useState<ReviewItem[]>([]);
  const [comments, setComments] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");

  const load = useCallback(async () => {
    setError("");
    const queue = await apiRequest<ReviewItem[]>(`orgs/${organizationId}/reviews/queue`);
    setRows(queue);
  }, [organizationId]);

  useEffect(() => {
    const timer = window.setTimeout(() => { load().catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "Could not load the review queue.")).finally(() => setLoading(false)); }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  const submissions = useMemo(() => {
    const grouped = new Map<string, Submission>();
    for (const row of rows) {
      const key = row.submission_id;
      const current = grouped.get(key);
      if (current) current.rows.push(row);
      else grouped.set(key, { organizationId, campaignId: row.campaign_id, campaignName: row.campaign_name, submissionId: key, rows: [row], createdAt: row.created_at });
    }
    return [...grouped.values()].sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  }, [rows, organizationId]);

  async function decide(submission: Submission, decision: "approve" | "reject" | "request_changes") {
    const comment = comments[submission.submissionId]?.trim() ?? "";
    if (decision !== "approve" && !comment) { setError("Add a comment before rejecting or requesting changes."); return; }
    setBusy(submission.submissionId); setError(""); setNotice("");
    try {
      await apiRequest<ReviewItem[]>(`orgs/${organizationId}/reviews/${submission.submissionId}/decision`, { method: "POST", body: JSON.stringify({ decision, comment: comment || null }) });
      await load(); setNotice(`Review ${decision.replaceAll("_", " ")} recorded for the submitted asset versions.`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not record the review decision."); }
    finally { setBusy(""); }
  }

  if (loading) return <div className="workspace-skeleton" aria-label="Loading review queue"><div/><div/></div>;
  return <>
    <header className="workspace-heading"><p className="eyebrow"><Link href={`/app/organisations/${organizationId}`}>Organisation</Link> / Reviews</p><h1>Reviewer queue</h1><p>Inspect current asset versions and scan evidence before recording a decision. Review decisions are stored with your account and timestamp.</p></header>
    {error && <p className="auth-message auth-error" role="alert">{error}</p>}{notice && <p className="auth-message auth-success" role="status">{notice}</p>}
    {submissions.length === 0 ? <section className="workspace-empty"><h2>Nothing is waiting for review</h2><p>New campaign submissions will appear here.</p></section> : <div className="review-queue">{submissions.map((submission) => <article className="workspace-section" key={submission.submissionId}><p className="eyebrow">Submitted {new Date(submission.createdAt).toLocaleString()}</p><h2>{submission.campaignName}</h2><p>{submission.rows.length} current asset version{submission.rows.length === 1 ? "" : "s"} submitted.</p><ul>{submission.rows.map((row) => <li key={row.id}>Asset <code>{row.asset_id}</code> · version {row.asset_version}</li>)}</ul><p><Link className="text-link" href={`/app/organisations/${organizationId}/campaigns/${submission.campaignId}`}>Open campaign findings and evidence</Link></p><label className="form-field">Reviewer comment<input value={comments[submission.submissionId] ?? ""} onChange={(event) => setComments((state) => ({ ...state, [submission.submissionId]: event.target.value }))} maxLength={1000}/></label><div className="inline-actions"><button className="small-button" type="button" disabled={busy === submission.submissionId} onClick={() => void decide(submission, "approve")}>Approve</button><button className="small-button" type="button" disabled={busy === submission.submissionId} onClick={() => void decide(submission, "request_changes")}>Request changes</button><button className="small-button" type="button" disabled={busy === submission.submissionId} onClick={() => void decide(submission, "reject")}>Reject</button></div></article>)}</div>}
  </>;
}

