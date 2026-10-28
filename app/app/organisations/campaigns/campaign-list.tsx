"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiRequest } from "@/app/lib/api-client";
import { useLocale } from "@/app/i18n";

type Campaign = { id: string; name: string; channels: string[]; starts_at: string | null; ends_at: string | null; language: string; status: string; version: number; created_at: string };
type OrgSummary = { id: string; role: string };

const channelOptions = ["Instagram caption", "Email", "Poster", "LinkedIn post"];

export function CampaignList({ organizationId }: { organizationId: string }) {
  const { t } = useLocale();
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
      setNotice(t("campaigns.created"));
      formElement.reset();
      await load();
      router.push(`/app/organisations/${organizationId}/campaigns/${campaign.id}`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : t("campaigns.createError")); }
    finally { setBusy(false); }
  }

  return <>
    <header className="workspace-heading"><p className="eyebrow"><Link href={`/app/organisations/${organizationId}`}>{t("nav.overview")}</Link> / {t("campaigns.title")}</p><h1>{t("campaigns.title")}</h1><p>{t("campaigns.intro")}</p></header>
    {error && <p className="auth-message auth-error" role="alert">{error}</p>}{notice && <p className="auth-message auth-success" role="status">{notice}</p>}
    {(role === "admin" || role === "creator") && <section className="workspace-section"><p className="eyebrow">{t("campaigns.new")}</p><h2>{t("campaigns.scope")}</h2><form className="campaign-create-form" onSubmit={create}><label className="form-field">{t("campaigns.name")}<input name="name" required minLength={2} maxLength={240}/></label><fieldset className="campaign-channels"><legend>{t("campaigns.channels")}</legend>{channelOptions.map((channel) => <label key={channel}><input type="checkbox" name="channels" value={channel} />{channel}</label>)}</fieldset><div className="rule-date-fields"><label className="form-field">{t("campaigns.starts")}<input type="date" name="starts_at"/></label><label className="form-field">{t("campaigns.ends")}<input type="date" name="ends_at"/></label></div><label className="form-field">{t("campaigns.contentLanguage")}<select name="language" defaultValue="en"><option value="en">English (en)</option><option value="hi">हिन्दी (hi)</option><option value="mr">मराठी (mr)</option></select></label><button className="button button-primary" disabled={busy}>{busy ? t("campaigns.creating") : t("campaigns.create")}</button></form></section>}
    <section className="workspace-section"><p className="eyebrow">{t("campaigns.register")}</p><h2>{t("campaigns.current")}</h2>{loading ? <div className="workspace-skeleton" aria-label={t("campaigns.loading")}><div/><div/></div> : campaigns.length === 0 ? <div className="workspace-empty"><h3>{t("campaigns.none")}</h3><p>{t("campaigns.noneHint")}</p></div> : <div className="campaign-list">{campaigns.map((campaign) => <Link className="campaign-row" href={`/app/organisations/${organizationId}/campaigns/${campaign.id}`} key={campaign.id}><span><strong>{campaign.name}</strong><small>{campaign.channels.join(" · ")} · {campaign.language}</small></span><span>{campaign.starts_at ?? t("campaigns.noStart")} – {campaign.ends_at ?? t("campaigns.noEnd")}</span></Link>)}</div>}<Link className="text-link" href={`/app/organisations/${organizationId}/campaign-health`}>{t("campaigns.healthLink")}</Link></section>
  </>;
}
