"use client";

import { FormEvent, useState } from "react";
import { apiRequest } from "@/app/lib/api-client";

type Citation = { source_id: string; source_title: string; source_version: number; passage_id: string; page_number: number | null; location_label: string | null; excerpt: string };
type Answer = { answer: string; insufficient_evidence: boolean; citations: Citation[]; maturity: string };

export function BrandTwin({ organizationId }: { organizationId: string }) {
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function ask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setAnswer(null); setBusy(true);
    const question = String(new FormData(event.currentTarget).get("question") ?? "").trim();
    try { setAnswer(await apiRequest<Answer>(`orgs/${organizationId}/brand-twin/ask`, { method: "POST", body: JSON.stringify({ question }) })); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not search approved evidence."); }
    finally { setBusy(false); }
  }

  return <section className="workspace-section brand-twin"><p className="eyebrow">Brand Twin · bounded prototype</p><h2>Ask the approved source library</h2><p>Answers quote relevant approved passages using local lexical retrieval. It does not use an LLM and refuses when the source library has no matching evidence.</p>
    <form className="asset-upload-form" onSubmit={ask}><label className="form-field">Question<input name="question" minLength={3} maxLength={1000} placeholder="What does the approved guidance say about the offer?" required/></label><button className="button button-primary" disabled={busy}>{busy ? "Searching approved sources…" : "Ask Brand Twin"}</button></form>
    {error && <p className="auth-message auth-error" role="alert">{error}</p>}
    {answer && <div className="brand-twin-result" role="status"><p>{answer.answer}</p>{answer.insufficient_evidence && <p><strong>Insufficient approved evidence.</strong> Ask an Admin to review the approved source library.</p>}{answer.citations.map((citation) => <blockquote className="brand-twin-citation" key={citation.passage_id}>{citation.excerpt}<small>{citation.source_title} · v{citation.source_version} · {citation.page_number ? `page ${citation.page_number}` : citation.location_label ?? "location not available"} · passage {citation.passage_id}</small></blockquote>)}<small>Maturity: {answer.maturity}</small></div>}
  </section>;
}
