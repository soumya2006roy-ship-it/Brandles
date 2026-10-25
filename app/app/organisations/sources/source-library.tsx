"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { apiRequest } from "@/app/lib/api-client";

type Source = { id: string; family_id: string; title: string; original_filename: string; content_type: string; sha256: string; size_bytes: number; version: number; status: "draft" | "approved" | "archived"; effective_from: string | null; effective_to: string | null; created_by: string; approved_by: string | null; approved_at: string | null; created_at: string };
type Passage = { id: string; text: string; page_number: number | null; location_label: string | null; start_offset: number | null; end_offset: number | null };
type SourceDetail = Source & { passages: Passage[] };
type OrgSummary = { id: string; role: string };

function Highlight({ text, query }: { text: string; query: string }) {
  if (!query.trim()) return <>{text}</>;
  const escaped = query.trim().replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const parts = text.split(new RegExp(`(${escaped})`, "ig"));
  return <>{parts.map((part, index) => part.toLocaleLowerCase() === query.trim().toLocaleLowerCase() ? <mark key={index}>{part}</mark> : part)}</>;
}

export function SourceLibrary({ organizationId }: { organizationId: string }) {
  const [sources, setSources] = useState<Source[]>([]);
  const [selected, setSelected] = useState<SourceDetail | null>(null);
  const [role, setRole] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [passageQuery, setPassageQuery] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const loadSources = useCallback(async () => {
    const [orgs, rows] = await Promise.all([
      apiRequest<OrgSummary[]>("orgs"),
      apiRequest<Source[]>(`orgs/${organizationId}/sources?${new URLSearchParams({ ...(query ? { query } : {}), ...(status ? { status } : {}) })}`),
    ]);
    setRole(orgs.find((org) => org.id === organizationId)?.role ?? "");
    setSources(rows);
  }, [organizationId, query, status]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setLoading(true);
      loadSources().catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "Could not load approved sources.")).finally(() => setLoading(false));
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadSources]);

  const groups = useMemo(() => {
    const map = new Map<string, Source[]>();
    for (const source of sources) map.set(source.family_id, [...(map.get(source.family_id) ?? []), source]);
    return [...map.values()].map((versions) => versions.sort((a, b) => b.version - a.version));
  }, [sources]);

  async function openSource(source: Source) {
    setError("");
    try { setSelected(await apiRequest<SourceDetail>(`orgs/${organizationId}/sources/${source.id}${passageQuery ? `?query=${encodeURIComponent(passageQuery)}` : ""}`)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not open this source version."); }
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    setError(""); setNotice(""); setBusy(true);
    const body = new FormData(formElement);
    try {
      const source = await apiRequest<Source>(`orgs/${organizationId}/sources`, { method: "POST", body });
      setNotice(`Version ${source.version} was uploaded as a draft. An Admin must approve it before campaign checks can use it.`);
      formElement.reset();
      await loadSources();
      await openSource(source);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not upload this source."); }
    finally { setBusy(false); }
  }

  async function approve(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    setError(""); setNotice(""); setBusy(true);
    const fields = new FormData(event.currentTarget);
    try {
      const updated = await apiRequest<Source>(`orgs/${organizationId}/sources/${selected.id}/approve`, { method: "POST", body: JSON.stringify({ effective_from: fields.get("effective_from") || null, effective_to: fields.get("effective_to") || null }) });
      setNotice(`Version ${updated.version} is approved. This approval is recorded in the source history.`);
      await loadSources();
      await openSource(updated);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not approve this source version."); }
    finally { setBusy(false); }
  }

  async function download(source: Source) {
    try {
      const result = await apiRequest<{ url: string }>(`orgs/${organizationId}/sources/${source.id}/download`);
      window.open(result.url, "_blank", "noopener,noreferrer");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not open the original file."); }
  }

  return <>
    <header className="workspace-heading"><p className="eyebrow"><Link href={`/app/organisations/${organizationId}`}>Organisation</Link> / Ground truth</p><h1>Approved sources</h1><p>Only Admin-approved, effective source versions are eligible as evidence for future checks. Uploads remain drafts until reviewed.</p></header>
    {error && <p className="auth-message auth-error" role="alert">{error}</p>}
    {notice && <p className="auth-message auth-success" role="status">{notice}</p>}
    {role === "admin" && <section className="workspace-section"><p className="eyebrow">Add a version</p><h2>Upload a source document or logo</h2><p>Supported files: PDF, DOCX, TXT, Markdown, PNG, JPEG, and WebP up to 20 MB. Documents are extracted and stored in passages with source locations. Approved logo files can be linked to an approved-logo rule. Local hashed lexical vectors are for prototype retrieval; they are not semantic embeddings.</p><form className="source-upload-form" onSubmit={upload}><label className="form-field">Document or logo title<input name="title" required minLength={2} maxLength={240} placeholder="Brand claims and substantiation"/></label><label className="form-field">File<input name="document" type="file" required accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.webp,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown,image/png,image/jpeg,image/webp"/></label><button className="button button-primary" disabled={busy}>{busy ? "Uploading…" : "Upload draft source"}</button></form></section>}

    <section className="source-layout"><div className="source-list-panel"><div className="source-filters"><label className="form-field">Search title or passages<input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search sources"/></label><label className="form-field">Status<select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">All versions</option><option value="draft">Draft</option><option value="approved">Approved</option><option value="archived">Archived</option></select></label></div>
      {loading ? <div className="workspace-skeleton" aria-label="Loading source library"><div/><div/><div/></div> : groups.length === 0 ? <div className="workspace-empty"><h2>No matching sources</h2><p>Upload a PDF, DOCX, text, or Markdown file as an Admin to begin the source library.</p></div> : groups.map((versions) => <section className="source-family" key={versions[0].family_id}><h2>{versions[0].title}</h2><ol>{versions.map((source) => <li key={source.id}><button className="source-version-button" type="button" onClick={() => void openSource(source)} aria-pressed={selected?.id === source.id}><span>Version {source.version} · {source.original_filename}</span><span className={`status-label status-${source.status}`}>{source.status}</span></button></li>)}</ol></section>)}
    </div>
    <section className="source-detail-panel" aria-live="polite">{selected ? <><p className="eyebrow">Version {selected.version} · {selected.status}</p><h2>{selected.title}</h2><p>{selected.original_filename} · {(selected.size_bytes / 1024).toFixed(0)} KB · SHA-256 <code>{selected.sha256.slice(0, 16)}…</code></p><button className="small-button" type="button" onClick={() => void download(selected)}>Download original</button>
      <div className="passage-search"><label className="form-field">Find within this document<input value={passageQuery} onChange={(event) => setPassageQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); void openSource(selected); } }} placeholder="Search passage text"/></label><button className="small-button" type="button" onClick={() => void openSource(selected)}>Find</button></div>
      {selected.status === "draft" && role === "admin" && <form className="source-approval-form" onSubmit={approve}><h3>Admin approval</h3><label className="form-field">Effective from<input type="date" name="effective_from"/></label><label className="form-field">Expiry date<input type="date" name="effective_to"/></label><button className="button button-primary" disabled={busy}>Approve source version</button></form>}
      <h3>Extracted passages ({selected.passages.length})</h3>{selected.passages.length === 0 ? <p>No passages match this search.</p> : <ol className="passage-list">{selected.passages.map((passage) => <li key={passage.id}><p className="eyebrow">{passage.location_label ?? (passage.page_number ? `Page ${passage.page_number}` : "Document text")}{passage.page_number && passage.location_label ? ` · page ${passage.page_number}` : ""}</p><blockquote><Highlight text={passage.text} query={passageQuery}/></blockquote><p><Link href={`/app/organisations/${organizationId}/rules?passage=${passage.id}`}>Create a rule from this passage</Link></p></li>)}</ol>}
    </> : <div className="workspace-empty"><h2>Choose a source version</h2><p>Open a version to inspect its extracted passages, approval dates, and source history.</p></div>}</section></section>
  </>;
}
