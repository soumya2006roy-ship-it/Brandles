"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { apiRequest } from "@/app/lib/api-client";

type Analytics = {
  period: { from: string; to: string; granularity: "daily" | "weekly" };
  summary: { compliance_score: number | null; open_findings: number; open_findings_percentage: number; average_review_minutes: number | null; scans: number; completed_scans: number; findings: number };
  violations: { type: string; count: number; percentage: number; open_count: number }[];
  trend: { date: string; compliance_score: number | null; scans: number }[];
  review_times: { average_minutes: number | null; median_minutes: number | null; resolved_findings: number; decided_reviews: number; by_reviewer: { reviewer_id: string; reviewer_name: string; average_minutes: number; decisions: number }[] };
  confusing_rules: { rule_id: string; finding_type: string; count: number; dismissal_rate: number; repeat_rate: number; suggested_action: string }[];
  campaigns: { campaign_id: string; campaign_name: string; channels: string[]; assets: number; scans: number; compliance_score: number | null; violation_rate: number; open_findings: number; average_turnaround_minutes: number | null }[];
};
type CampaignOption = { id: string; name: string };
type Filters = { start: string; end: string; campaign: string; content: string; severity: string };

function dateInput(daysAgo: number) {
  const value = new Date();
  value.setDate(value.getDate() - daysAgo);
  return value.toISOString().slice(0, 10);
}

function formatDuration(minutes: number | null) {
  if (minutes === null) return "—";
  if (minutes < 60) return `${Math.round(minutes)} min`;
  const hours = minutes / 60;
  return `${hours < 10 ? hours.toFixed(1) : Math.round(hours)} hr`;
}

function safeCsvCell(value: unknown) {
  const raw = String(value ?? "");
  const protectedValue = /^[\s]*[=+\-@]/.test(raw) ? `'${raw}` : raw;
  return `"${protectedValue.replaceAll('"', '""')}"`;
}

function ComplianceTrend({ rows }: { rows: Analytics["trend"] }) {
  const valid = rows.filter((row) => row.compliance_score !== null);
  if (!valid.length) return <p className="analytics-chart-empty">Completed scans will appear here once this date range has results.</p>;
  const width = Math.max(640, valid.length * 30);
  const height = 220;
  const points = valid.map((row, index) => ({ x: valid.length === 1 ? width / 2 : 18 + index * (width - 36) / (valid.length - 1), y: height - 22 - Number(row.compliance_score) * 1.65, ...row }));
  const path = points.map((point, index) => `${index ? "L" : "M"}${point.x},${point.y}`).join(" ");
  const label = points.map((point) => `${point.date}: ${point.compliance_score}% compliance from ${point.scans} scan(s)`).join("; ");
  return <div className="analytics-chart-scroll"><svg className="analytics-trend-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`Compliance trend: ${label}`}>
    {[0, 25, 50, 75, 100].map((score) => <g key={score}><line x1="18" x2={width - 18} y1={height - 22 - score * 1.65} y2={height - 22 - score * 1.65} className="analytics-grid-line"/><text x="0" y={height - 18 - score * 1.65} className="analytics-axis-label">{score}</text></g>)}
    <path d={`${path} L${points.at(-1)?.x},${height - 22} L${points[0].x},${height - 22} Z`} className="analytics-trend-area"/>
    <path d={path} className="analytics-trend-line"/>
    {points.map((point) => <g key={point.date}><circle cx={point.x} cy={point.y} r="4" className="analytics-trend-point"><title>{point.date}: {point.compliance_score}%</title></circle><text x={point.x} y={height - 4} textAnchor="middle" className="analytics-date-label">{point.date.slice(5)}</text></g>)}
  </svg></div>;
}

export function BrandHealthDashboard({ organizationId }: { organizationId: string }) {
  const [filters, setFilters] = useState<Filters>({ start: dateInput(29), end: dateInput(0), campaign: "", content: "", severity: "" });
  const [draft, setDraft] = useState(filters);
  const [campaignOptions, setCampaignOptions] = useState<CampaignOption[]>([]);
  const [data, setData] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const query = useMemo(() => {
    const params = new URLSearchParams({ start_date: filters.start, end_date: filters.end });
    if (filters.campaign) params.set("campaign_id", filters.campaign);
    if (filters.content) params.set("content_type", filters.content);
    if (filters.severity) params.set("severity", filters.severity);
    return params.toString();
  }, [filters]);

  const loadData = useCallback(async () => {
    try {
      const result = await apiRequest<Analytics>(`orgs/${organizationId}/analytics/brand-health?${query}`);
      setData(result);
      setError("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load Brand Health right now.");
    } finally {
      setLoading(false);
    }
  }, [organizationId, query]);

  useEffect(() => {
    let active = true;
    apiRequest<CampaignOption[]>(`orgs/${organizationId}/campaigns`)
      .then((rows) => { if (active) setCampaignOptions(rows.map(({ id, name }) => ({ id, name }))); })
      .catch(() => { if (active) setCampaignOptions([]); });
    return () => { active = false; };
  }, [organizationId]);

  useEffect(() => {
    const timer = window.setTimeout(() => { void loadData(); }, 0);
    return () => window.clearTimeout(timer);
  }, [loadData]);

  function exportCsv() {
    if (!data) return;
    const rows: unknown[][] = [["section", "name", "value", "detail"],
      ["summary", "compliance_score", data.summary.compliance_score ?? "No completed scans", "percent"],
      ["summary", "open_findings", data.summary.open_findings, `${data.summary.open_findings_percentage}% of findings`],
      ["summary", "average_review_time_minutes", data.summary.average_review_minutes ?? "No review data", "minutes"],
      ["summary", "scans", data.summary.scans, "selected period"],
      ...data.violations.map((row) => ["violation", row.type, row.count, `${row.percentage}% total; ${row.open_count} open`]),
      ...data.trend.map((row) => ["trend", row.date, row.compliance_score ?? "No scan", `${row.scans} scans`]),
      ...data.confusing_rules.map((row) => ["rule", row.rule_id, row.dismissal_rate, `${row.repeat_rate}% repeat; ${row.suggested_action}`]),
      ...data.campaigns.map((row) => ["campaign", row.campaign_name, row.compliance_score ?? "No completed scan", `${row.open_findings} open findings; ${row.violation_rate}% assets with findings; ${formatDuration(row.average_turnaround_minutes)}`])];
    const content = rows.map((row) => row.map(safeCsvCell).join(",")).join("\r\n");
    const url = URL.createObjectURL(new Blob([content], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `brand-health-${filters.start}-to-${filters.end}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  const applyFilters = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setFilters(draft);
  };

  return <>
    <header className="workspace-heading"><p className="eyebrow"><Link href={`/app/organisations/${organizationId}`}>Workspace</Link> / Brand health</p><h1>Brand Health</h1><p>See recurring governance issues, compliance movement, and review patterns across your campaigns.</p></header>
    <form className="analytics-filters workspace-section" onSubmit={applyFilters} aria-label="Filter brand health metrics">
      <label className="form-field">From<input type="date" value={draft.start} max={draft.end} onChange={(event) => setDraft({ ...draft, start: event.target.value })} required/></label>
      <label className="form-field">To<input type="date" value={draft.end} min={draft.start} onChange={(event) => setDraft({ ...draft, end: event.target.value })} required/></label>
      <label className="form-field">Campaign<select value={draft.campaign} onChange={(event) => setDraft({ ...draft, campaign: event.target.value })}><option value="">All campaigns</option>{campaignOptions.map((campaign) => <option key={campaign.id} value={campaign.id}>{campaign.name}</option>)}</select></label>
      <label className="form-field">Content type<select value={draft.content} onChange={(event) => setDraft({ ...draft, content: event.target.value })}><option value="">All content</option><option value="text">Text</option><option value="image">Image</option><option value="document">Document</option></select></label>
      <label className="form-field">Severity<select value={draft.severity} onChange={(event) => setDraft({ ...draft, severity: event.target.value })}><option value="">All severities</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></label>
      <div className="analytics-filter-actions"><button type="submit" className="button button-primary">Apply filters</button><button type="button" className="button secondary-button" onClick={exportCsv} disabled={!data}>Export CSV</button></div>
    </form>
    {loading ? <section className="workspace-section" aria-live="polite"><p>Loading brand health data…</p><div className="workspace-skeleton"><div/><div/><div/></div></section> : error ? <section className="workspace-section"><p className="auth-message auth-error" role="alert">{error}</p><button type="button" className="button secondary-button" onClick={() => { setLoading(true); void loadData(); }}>Try again</button></section> : !data || data.summary.scans === 0 ? <section className="workspace-empty" role="status"><h2>No scan data in this range</h2><p>Try a wider date range or run a scan on one of your campaigns.</p><Link className="button secondary-button" href={`/app/organisations/${organizationId}/campaigns`}>View campaigns</Link></section> : <>
      <section className="analytics-kpis" aria-label="Brand health summary">
        <article className="analytics-kpi"><span>Compliance score</span><strong>{data.summary.compliance_score === null ? "—" : `${data.summary.compliance_score}%`}</strong><small>Severity-weighted open findings per asset</small></article>
        <article className="analytics-kpi"><span>Open findings</span><strong>{data.summary.open_findings}</strong><small>{data.summary.open_findings_percentage}% of findings in this view</small></article>
        <article className="analytics-kpi"><span>Average review time</span><strong>{formatDuration(data.summary.average_review_minutes)}</strong><small>From scan to resolution or review decision</small></article>
        <article className="analytics-kpi"><span>Scans this period</span><strong>{data.summary.scans}</strong><small>{data.summary.completed_scans} completed</small></article>
      </section>
      <section className="workspace-section analytics-section"><div className="analytics-section-heading"><div><p className="eyebrow">Movement</p><h2>Compliance trend</h2></div><span>{data.period.granularity} view</span></div><ComplianceTrend rows={data.trend}/></section>
      <div className="analytics-grid">
        <section className="workspace-section analytics-section"><p className="eyebrow">What gets flagged</p><h2>Top violations</h2>{data.violations.length ? <ol className="analytics-violations">{data.violations.slice(0, 8).map((row) => <li key={row.type}><span><strong>{row.type.replaceAll("_", " ")}</strong><small>{row.open_count} open · {row.percentage}% of findings</small></span><b>{row.count}</b><span className="analytics-bar-track" aria-hidden="true"><span style={{ width: `${Math.max(2, row.percentage)}%` }}/></span></li>)}</ol> : <p className="analytics-chart-empty">No violations match these filters.</p>}</section>
        <section className="workspace-section analytics-section"><p className="eyebrow">Review insights</p><h2>Rules to revisit</h2><p className="analytics-explainer">A rule is surfaced when at least 25% of its findings were dismissed or at least 30% are repeat flags in this date range. Repeats are a signal, not proof of a faulty rule.</p>{data.confusing_rules.length ? <div className="analytics-table-scroll"><table className="analytics-table"><thead><tr><th>Rule / finding</th><th>Dismissed</th><th>Repeat</th><th>Suggested action</th></tr></thead><tbody>{data.confusing_rules.map((row) => <tr key={row.rule_id}><td>{row.finding_type.replaceAll("_", " ")}</td><td>{row.dismissal_rate}%</td><td>{row.repeat_rate}%</td><td>{row.suggested_action}</td></tr>)}</tbody></table></div> : <p className="analytics-chart-empty">No rule crossed the review thresholds.</p>}</section>
      </div>
      <section className="workspace-section analytics-section"><p className="eyebrow">Review turnaround</p><h2>Time to decision</h2><div className="analytics-review-summary"><span>Median: <strong>{formatDuration(data.review_times.median_minutes)}</strong></span><span>Resolved findings: <strong>{data.review_times.resolved_findings}</strong></span><span>Review decisions: <strong>{data.review_times.decided_reviews}</strong></span></div>{data.review_times.by_reviewer.length > 0 && <div className="analytics-table-scroll"><table className="analytics-table"><thead><tr><th>Reviewer</th><th>Average time</th><th>Decisions</th></tr></thead><tbody>{data.review_times.by_reviewer.map((row) => <tr key={row.reviewer_id}><td>{row.reviewer_name}</td><td>{formatDuration(row.average_minutes)}</td><td>{row.decisions}</td></tr>)}</tbody></table></div>}</section>
      <section className="workspace-section analytics-section"><p className="eyebrow">Campaign comparison</p><h2>Governance by campaign</h2>{data.campaigns.length ? <div className="analytics-table-scroll"><table className="analytics-table"><thead><tr><th>Campaign</th><th>Channels</th><th>Assets</th><th>Scans</th><th>Compliance</th><th>Assets with findings</th><th>Average turnaround</th><th>Open</th></tr></thead><tbody>{data.campaigns.map((row) => <tr key={row.campaign_id}><td><Link href={`/app/organisations/${organizationId}/campaigns/${row.campaign_id}`}>{row.campaign_name}</Link></td><td>{row.channels.join(", ")}</td><td>{row.assets}</td><td>{row.scans}</td><td>{row.compliance_score === null ? "—" : `${row.compliance_score}%`}</td><td>{row.violation_rate}%</td><td>{formatDuration(row.average_turnaround_minutes)}</td><td>{row.open_findings}</td></tr>)}</tbody></table></div> : <p className="analytics-chart-empty">No campaigns match these filters.</p>}</section>
    </>}
  </>;
}
