"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { apiRequest, type Invite, type Organization, type OrganizationSummary } from "@/app/lib/api-client";

type NewInvite = Invite & { code: string };
type WorkspaceNotification = { id: string; kind: string; payload: Record<string, unknown>; read_at: string | null; created_at: string };

export function OrganisationWorkspace({ organizationId }: { organizationId: string }) {
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [role, setRole] = useState<string>("");
  const [invites, setInvites] = useState<Invite[]>([]);
  const [notifications, setNotifications] = useState<WorkspaceNotification[]>([]);
  const [newInvite, setNewInvite] = useState<NewInvite | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError("");
    try {
      const org = await apiRequest<Organization>(`orgs/${organizationId}`);
      setOrganization(org);
      const list = await apiRequest<OrganizationSummary[]>("orgs");
      setRole(list.find((item) => item.id === organizationId)?.role ?? "");
      if (org.verification_status === "approved") setNotifications(await apiRequest<WorkspaceNotification[]>(`orgs/${organizationId}/notifications`));
      if (org.verification_status === "approved" && list.find((item) => item.id === organizationId)?.role === "admin") {
        setInvites(await apiRequest<Invite[]>(`orgs/${organizationId}/invites`));
      }
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not load this organisation."); }
    finally { setLoading(false); }
  }, [organizationId]);

  useEffect(() => {
    const timer = window.setTimeout(() => { void load(); }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  async function createInvite(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      const invite = await apiRequest<NewInvite>(`orgs/${organizationId}/invites`, { method: "POST", body: JSON.stringify({ role: data.get("role"), expires_in_days: Number(data.get("expires_in_days")), usage_limit: Number(data.get("usage_limit")) }) });
      setNewInvite(invite);
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not create an invite."); }
  }

  async function revoke(inviteId: string) {
    try { await apiRequest<void>(`orgs/${organizationId}/invites/${inviteId}`, { method: "DELETE" }); await load(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not revoke the invite."); }
  }

  async function regenerate(inviteId: string) {
    try {
      const invite = await apiRequest<NewInvite>(`orgs/${organizationId}/invites/${inviteId}/regenerate`, { method: "POST" });
      setNewInvite(invite);
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not regenerate the invite."); }
  }

  async function updateAiPreference(allowed: boolean) {
    try {
      const result = await apiRequest<{ llm_processing_allowed: boolean }>(`orgs/${organizationId}/settings`, { method: "PATCH", body: JSON.stringify({ llm_processing_allowed: allowed }) });
      setOrganization((current) => current ? { ...current, llm_processing_allowed: result.llm_processing_allowed } : current);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not update the AI processing setting."); }
  }

  async function markRead(notificationId: string) {
    try {
      const updated = await apiRequest<WorkspaceNotification>(`orgs/${organizationId}/notifications/${notificationId}/read`, { method: "POST" });
      setNotifications((items) => items.map((item) => item.id === notificationId ? updated : item));
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not update this notification."); }
  }

  if (loading) return <div className="workspace-skeleton" aria-label="Loading organisation"><div/><div/></div>;
  if (!organization) return <p className="auth-message auth-error" role="alert">{error || "Organisation not found."}</p>;
  const canManage = role === "admin" && organization.verification_status === "approved";
  return <>
    <header className="workspace-heading"><p className="eyebrow">{organization.industry} · {role}</p><h1>{organization.name}</h1><p>{organization.official_email} · <a href={organization.website} target="_blank" rel="noreferrer">Organisation website</a></p><span className={`status-label status-${organization.verification_status}`}>{organization.verification_status.replaceAll("_", " ")}</span></header>
    {organization.verification_status === "pending_verification" && <section className="workspace-notice"><h2>Waiting for platform verification</h2><p>An administrator will review the organisation details. You cannot invite members or add sources until the workspace is approved.</p></section>}
    {organization.verification_status === "more_information_required" && <section className="workspace-notice"><h2>More information is required</h2><p>Check with the platform team for the details needed to continue. Organisation resubmission is not available yet.</p></section>}
    {organization.verification_status === "rejected" && <section className="workspace-notice"><h2>Organisation not approved</h2><p>Workspace actions are unavailable. Contact the platform team if you believe this decision needs review.</p></section>}
    {error && <p className="auth-message auth-error" role="alert">{error}</p>}
    {canManage && <section className="workspace-section"><div className="workspace-section-heading"><div><p className="eyebrow">Access</p><h2>Invite organisation members</h2><p>Create a role-scoped code. It is shown once and is never added to a URL.</p></div></div>
      <form className="invite-form" onSubmit={createInvite}><label className="form-field">Role<select name="role" defaultValue="creator"><option value="admin">Admin</option><option value="creator">Creator</option><option value="reviewer">Reviewer</option></select></label><label className="form-field">Expires in days<input name="expires_in_days" type="number" min={1} max={30} defaultValue={7}/></label><label className="form-field">Uses<input name="usage_limit" type="number" min={1} max={100} defaultValue={1}/></label><button className="button button-primary" type="submit">Create invite code</button></form>
      {newInvite && <div className="one-time-code" role="status"><strong>Copy this invite code now</strong><p>This code is only shown in the creation response. Share it with the intended organisation member using a trusted channel.</p><code>{newInvite.code}</code><button className="small-button" type="button" onClick={() => navigator.clipboard.writeText(newInvite.code).catch(() => setError("Clipboard access is unavailable. Select and copy the code instead."))}>Copy code</button></div>}
      <h3>Active and revoked codes</h3>{invites.length ? <ul className="invite-list">{invites.map((invite) => <li key={invite.id}><div><strong>{invite.role}</strong><span>{invite.usage_count}/{invite.usage_limit} uses · expires {new Date(invite.expires_at).toLocaleDateString()}</span></div>{invite.revoked_at ? <span className="status-label">Revoked</span> : <div className="inline-actions"><button className="small-button" type="button" onClick={() => regenerate(invite.id)}>Regenerate</button><button className="small-button" type="button" onClick={() => revoke(invite.id)}>Revoke</button></div>}</li>)}</ul> : <p>No invite codes yet.</p>}
    </section>}
    {organization.verification_status === "approved" && <section className="workspace-section"><p className="eyebrow">Notifications</p><h2>Workspace activity</h2>{notifications.length ? <ul className="invite-list">{notifications.map((notification) => <li key={notification.id}><div><strong>{notification.kind.replaceAll("_", " ")}</strong><span>{String(notification.payload.campaign_name ?? notification.payload.organization_name ?? "Workspace update")} · {new Date(notification.created_at).toLocaleString()}</span></div>{notification.read_at ? <span>Read</span> : <button className="small-button" type="button" onClick={() => void markRead(notification.id)}>Mark read</button>}</li>)}</ul> : <div className="workspace-empty"><p>No notifications yet.</p></div>}</section>}
    {canManage && <section className="workspace-section"><p className="eyebrow">AI processing</p><h2>Workspace permission</h2><p>External model processing is off by default. BrandLens will not send workspace material to an LLM unless both this organisation and the deployment allow it.</p><p className="settings-state">Current setting: <strong>{organization.llm_processing_allowed ? "Allowed" : "Off"}</strong></p><button className="button secondary-button" type="button" onClick={() => updateAiPreference(!organization.llm_processing_allowed)}>{organization.llm_processing_allowed ? "Turn off AI processing" : "Allow AI processing"}</button><p className="field-help">This repository has no live LLM provider adapter; the mock returns insufficient evidence only.</p></section>}
    {organization.verification_status === "approved" && <section className="workspace-scope"><p className="eyebrow">Product scope</p><p>Approved sources, structured rules, campaign scans, findings and reviewer decisions are available. Model judgement remains a mock prototype.</p></section>}
    {organization.verification_status === "approved" && <section className="workspace-section"><p className="eyebrow">Workspace library</p><h2>Sources, rules, and campaigns</h2><div className="workspace-quicklinks"><Link className="button secondary-button" href={`/app/organisations/${organizationId}/sources`}>Approved sources</Link><Link className="button secondary-button" href={`/app/organisations/${organizationId}/rules`}>Structured rules</Link><Link className="button secondary-button" href={`/app/organisations/${organizationId}/campaigns`}>Campaigns</Link>{role === "reviewer" && <Link className="button secondary-button" href={`/app/organisations/${organizationId}/reviews`}>Review queue</Link>}</div></section>}
  </>;
}
