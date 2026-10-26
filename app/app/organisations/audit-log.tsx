"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiRequest } from "@/app/lib/api-client";

type Event = { id: string; actor_user_id: string | null; actor_name: string | null; action: string; entity_type: string; entity_id: string; details: Record<string, unknown>; created_at: string };

export function AuditLog({ organizationId }: { organizationId: string }) {
  const [events, setEvents] = useState<Event[]>([]);
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const limit = 50;
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { const params = new URLSearchParams({ offset: String(offset), limit: String(limit) }); if (appliedSearch) params.set("action", appliedSearch); setEvents(await apiRequest<Event[]>(`orgs/${organizationId}/audit-events?${params}`)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not load the audit log."); }
    finally { setLoading(false); }
  }, [organizationId, appliedSearch, offset]);
  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);
  function searchEvents(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setOffset(0); setAppliedSearch(search.trim()); }
  return <>
    <header className="workspace-heading"><p className="eyebrow"><Link href={`/app/organisations/${organizationId}`}>Workspace</Link> / Audit</p><h1>Audit log</h1><p>Append-only record of organisation actions. Secret values and document contents are not shown here.</p></header>
    <section className="workspace-section"><form className="finding-filters" onSubmit={searchEvents}><label className="form-field">Filter by action<input value={search} onChange={(event) => setSearch(event.target.value)} maxLength={80} placeholder="review, source, scan…"/></label><button className="small-button" type="submit">Search log</button></form>
      {error && <p className="auth-message auth-error" role="alert">{error}</p>}
      {loading ? <div className="workspace-skeleton" aria-label="Loading audit log"><div/><div/><div/></div> : events.length === 0 ? <div className="workspace-empty"><h2>No audit events found</h2><p>Try another action filter or return when the workspace has activity.</p></div> : <ol className="audit-event-list">{events.map((event) => <li key={event.id}><div className="audit-event-head"><strong>{event.action.replaceAll(".", " · ").replaceAll("_", " ")}</strong><time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString()}</time></div><p>{event.actor_name ?? "Former member"} · {event.entity_type} · <code>{event.entity_id}</code></p><details><summary>Event details</summary><pre>{JSON.stringify(event.details, null, 2)}</pre></details></li>)}</ol>}
      <div className="inline-actions"><button className="small-button" type="button" disabled={offset === 0 || loading} onClick={() => setOffset(Math.max(0, offset - limit))}>Previous</button><span>Showing {events.length ? offset + 1 : 0}–{offset + events.length}</span><button className="small-button" type="button" disabled={loading || events.length < limit} onClick={() => setOffset(offset + limit)}>Next</button></div>
    </section>
  </>;
}
