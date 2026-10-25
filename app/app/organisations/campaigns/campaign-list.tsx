"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiRequest } from "@/app/lib/api-client";

type Campaign = { id: string; name: string; channels: string[]; starts_at: string | null; ends_at: string | null; language: string; status: string; version: number; created_at: string };
type OrgSummary = { id: string; role: string };

const channelOptions = ["Instagram caption", "Email", "Poster", "LinkedIn post"];

export function CampaignList({ organizationId }: { organizationId: string }) {
  const router = useRouter();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [role, setRole] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const [orgs, rows] = await Promise.all([apiRequest<OrgSummary[]>("orgs"), apiRequest<Campaign[]>(`orgs/${organizationId}/campaigns`)]);
    setRole(orgs.find((org) => org.id === organizationId)?.role ?? "");
    setCampaigns(rows);
  }, [organizationId]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      load().catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "Could not load campaigns.")).finally(() => setLoading(false));
    }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    setError(""); setNotice(""); setBusy(true);
    try {
      const campaign = await apiRequest<Campaign>(`orgs/${organizationId}/campaigns`, { method: "POST", body: JSON.stringify({ name: form.get("name"), channels: form.getAll("channels"), starts_at: form.get("starts_at") || null, ends_at: form.get("ends_at") || null, language: form.get("language") }) });
      setNotice("Campaign created. Add a text asset or upload a file for each campaign channel.");
      formElement.reset();
      await load();
      router.push(`/app/organisations/${organizationId}/campaigns/${campaign.id}`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not create this campaign."); }
    finally { setBusy(false); }
  }

  return <>
    <header className="workspace-heading"><p className="eyebrow"><Link href={`/app/organisations/${organizationId}`}>Organisation</Link> / Campaigns</p><h1>Campaigns</h1><p>Plan a campaign window and the channels whose assets will be reviewed together.</p></header>
    {error && <p className="auth-message auth-error" role="alert">{error}</p>}{notice && <p className="auth-message auth-success" role="status">{notice}</p>}
    {(role === "admin" || role === "creator") && <section className="workspace-section"><p className="eyebrow">New campaign</p><h2>Set campaign scope</h2><form className="campaign-create-form" onSubmit={create}><label className="form-field">Campaign name<input name="name" required minLength={2} maxLength={240}/></label><fieldset className="campaign-channels"><legend>Channels</legend>{channelOptions.map((channel) => <label key={channel}><input type="checkbox" name="channels" value={channel} />{channel}</label>)}</fieldset><div className="rule-date-fields"><label className="form-field">Starts on<input type="date" name="starts_at"/></label><label className="form-field">Ends on<input type="date" name="ends_at"/></label></div><label className="form-field">Language code<input name="language" defaultValue="en" required minLength={2} maxLength={32} placeholder="en"/></label><button className="button button-primary" disabled={busy}>{busy ? "Creating…" : "Create campaign"}</button></form></section>}
    <section className="workspace-section"><p className="eyebrow">Campaign register</p><h2>Current campaigns</h2>{loading ? <div className="workspace-skeleton" aria-label="Loading campaigns"><div/><div/></div> : campaigns.length === 0 ? <div className="workspace-empty"><h3>No campaigns yet</h3><p>Create a campaign to start collecting channel assets.</p></div> : <div className="campaign-list">{campaigns.map((campaign) => <Link className="campaign-row" href={`/app/organisations/${organizationId}/campaigns/${campaign.id}`} key={campaign.id}><span><strong>{campaign.name}</strong><small>{campaign.channels.join(" · ")} · {campaign.language}</small></span><span>{campaign.starts_at ?? "No start"} – {campaign.ends_at ?? "No end"}</span></Link>)}</div>}</section>
  </>;
}
