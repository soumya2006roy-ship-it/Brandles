"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useLocale } from "@/app/i18n";
import { apiRequest } from "@/app/lib/api-client";

type Status = "healthy" | "warning" | "critical";
type Check = { key: string; status: "pass" | "warning" | "fail"; detail: string; recommendation: string };
type Health = { campaign_id: string; campaign_name: string; score: number; status: Status; checks: Check[]; recommendations: string[]; latest_scan_status: string | null; open_high_findings: number; updated_at: string };
type Overview = { healthy_count: number; warning_count: number; critical_count: number; campaigns: Health[] };
const PAGE_SIZE = 8;

export function CampaignHealth({ organizationId }: { organizationId: string }) {
  const { t } = useLocale();
  const [data, setData] = useState<Overview | null>(null);
  const [selected, setSelected] = useState<Health | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    apiRequest<Overview>(`orgs/${organizationId}/campaigns/health`)
      .then((result) => { if (active) { setData(result); setSelected(result.campaigns[0] ?? null); } })
      .catch((cause: unknown) => { if (active) setError(cause instanceof Error ? cause.message : t("health.error")); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [organizationId, t]);

  const filtered = useMemo(() => (data?.campaigns ?? []).filter((campaign) =>
    (filter === "all" || campaign.status === filter) && campaign.campaign_name.toLocaleLowerCase().includes(query.toLocaleLowerCase()),
  ), [data, filter, query]);
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageRows = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  function choose(campaign: Health) {
    setSelected(campaign);
  }

  return <>
    <header className="workspace-heading"><p className="eyebrow"><Link href={`/app/organisations/${organizationId}`}>{t("nav.overview")}</Link> / {t("health.title")}</p><h1>{t("health.title")}</h1><p>{t("health.intro")}</p></header>
    <p className="health-maturity" role="note">{t("health.prototype")}</p>
    {loading ? <section className="workspace-section" aria-live="polite"><p>{t("health.loading")}</p><div className="workspace-skeleton"><div/><div/><div/></div></section> : error ? <section className="workspace-section"><p className="auth-message auth-error" role="alert">{error}</p><button className="button secondary-button" onClick={() => window.location.reload()}>Retry</button></section> : !data ? <section className="workspace-empty" role="status">{t("health.error")}</section> : <>
      <section className="health-summary" aria-label={t("health.title")}>
        {(["healthy", "warning", "critical"] as const).map((status) => <div className={`health-summary-card status-${status}`} key={status}><span>{t(`health.${status}`)}</span><strong>{data[`${status}_count`]}</strong></div>)}
      </section>
      <section className="workspace-section">
        <div className="health-filters"><label className="form-field">{t("health.search")}<input value={query} onChange={(event) => { setQuery(event.target.value); setPage(0); }} type="search" placeholder={t("health.search")}/></label><label className="form-field">{t("health.all")}<select value={filter} onChange={(event) => { setFilter(event.target.value); setPage(0); }}><option value="all">{t("health.all")}</option><option value="healthy">{t("health.healthy")}</option><option value="warning">{t("health.warning")}</option><option value="critical">{t("health.critical")}</option></select></label></div>
        {filtered.length === 0 ? <div className="workspace-empty"><h2>{data.campaigns.length ? "No campaigns match" : t("health.empty")}</h2><p>{data.campaigns.length ? "Try a different search or status." : t("health.emptyHint")}</p></div> : <div className="health-layout">
          <div>
            <ul className="health-campaign-list" aria-label={t("health.campaigns")}>
              {pageRows.map((campaign) => <li key={campaign.campaign_id}><button type="button" className={`health-campaign-card${selected?.campaign_id === campaign.campaign_id ? " is-selected" : ""}`} onClick={() => choose(campaign)} aria-pressed={selected?.campaign_id === campaign.campaign_id}><span><strong>{campaign.campaign_name}</strong><small className={`health-status status-${campaign.status}`}>{t(`health.${campaign.status}`)}</small></span><b aria-label={`${campaign.score} ${t("health.score")}`}>{campaign.score}</b></button></li>)}
            </ul>
            <nav className="health-pagination" aria-label="Campaign health pages"><button className="button secondary-button" disabled={page === 0} onClick={() => setPage((value) => value - 1)}>Previous</button><span>Page {page + 1} / {pageCount}</span><button className="button secondary-button" disabled={page + 1 >= pageCount} onClick={() => setPage((value) => value + 1)}>Next</button></nav>
          </div>
          {selected && <article className="health-detail" aria-live="polite"><div className={`health-score status-${selected.status}`}><span>{t("health.score")}</span><strong>{selected.score}</strong><small>{t(`health.${selected.status}`)}</small></div><h2>{selected.campaign_name}</h2><p className="eyebrow">{t("health.checks")}</p><ul className="health-check-list">{selected.checks.map((check) => <li key={check.key}><span className={`health-check-icon check-${check.status}`} aria-hidden="true">{check.status === "pass" ? "✓" : "!"}</span><div><strong>{t(`health.${check.key}`)}</strong><p>{check.detail}</p>{check.recommendation && <small>{check.recommendation}</small>}</div></li>)}</ul><Link className="button secondary-button" href={`/app/organisations/${organizationId}/campaigns/${selected.campaign_id}`}>{t("health.openCampaign")}</Link></article>}
        </div>}
      </section>
    </>}
  </>;
}
