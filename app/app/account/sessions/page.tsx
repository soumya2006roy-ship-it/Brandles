"use client";

import { useCallback, useEffect, useState } from "react";
import { apiRequest } from "@/app/lib/api-client";

type Session = { id: string; created_at: string; expires_at: string; current: boolean };
export default function SessionsPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [error, setError] = useState("");
  const load = useCallback(() => apiRequest<Session[]>("auth/sessions").then(setSessions).catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "Could not load sessions.")), []);
  useEffect(() => { void load(); }, [load]);
  async function revoke(id: string) {
    try { await apiRequest<void>(`auth/sessions/${id}`, { method: "DELETE" }); await load(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not revoke session."); }
  }
  return <><header className="workspace-heading"><p className="eyebrow">Account security</p><h1>Your sessions</h1><p>Sessions are stored in HTTP-only cookies. Revoke any session you no longer use.</p></header>{error && <p className="auth-message auth-error" role="alert">{error}</p>}<ul className="session-list">{sessions.map((session) => <li key={session.id}><div><strong>{session.current ? "This session" : "Signed-in session"}</strong><span>Created {new Date(session.created_at).toLocaleString()} · expires {new Date(session.expires_at).toLocaleString()}</span></div><button className="small-button" type="button" onClick={() => revoke(session.id)}>Revoke</button></li>)}</ul></>;
}
