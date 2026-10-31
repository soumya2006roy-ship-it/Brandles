"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { apiRequest } from "@/app/lib/api-client";

type Source = { id: string; family_id: string; title: string; version: number; status: string };
type Passage = { id: string; text: string; page_number: number | null; location_label: string | null; source_id: string; source_title: string; source_version: number; source_status: string };
type Rule = { id: string; rule_type: string; parameters: Record<string, unknown>; channel: string | null; valid_from: string | null; valid_to: string | null; source_passage_id: string | null; status: string; created_by: string; created_at: string };
type OrganizationSummary = { id: string; role: string };
type RuleType = "offer_name" | "discount_percent" | "valid_from" | "valid_until" | "banned_phrase" | "required_disclaimer" | "approved_logo" | "channel_length_limit" | "brand_colors" | "typography";

const labels: Record<RuleType, string> = { offer_name: "Offer name", discount_percent: "Discount percentage", valid_from: "Offer starts on", valid_until: "Offer ends on", banned_phrase: "Banned phrase", required_disclaimer: "Required disclaimer", approved_logo: "Approved logo version", channel_length_limit: "Channel character limit", brand_colors: "Brand colour palette", typography: "Typography guidance" };

export function RulesEditor({ organizationId }: { organizationId: string }) {
  const params = useSearchParams();
  const passageIdFromUrl = params.get("passage") ?? "";
  const [sources, setSources] = useState<Source[]>([]);
  const [sourceId, setSourceId] = useState("");
  const [passages, setPassages] = useState<Passage[]>([]);
  const [passageId, setPassageId] = useState(passageIdFromUrl);
  const [rules, setRules] = useState<Rule[]>([]);
  const [role, setRole] = useState("");
  const [ruleType, setRuleType] = useState<RuleType>("offer_name");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const [orgs, sourceRows, ruleRows] = await Promise.all([
      apiRequest<OrganizationSummary[]>("orgs"),
      apiRequest<Source[]>(`orgs/${organizationId}/sources?status=approved`),
      apiRequest<Rule[]>(`orgs/${organizationId}/rules`),
    ]);
    setRole(orgs.find((org) => org.id === organizationId)?.role ?? "");
    setSources(sourceRows);
    setRules(ruleRows);
    if (!sourceId && sourceRows.length) setSourceId(sourceRows[0].id);
    if (passageIdFromUrl) {
      const passage = await apiRequest<Passage>(`orgs/${organizationId}/passages/${passageIdFromUrl}`);
      if (passage.source_status === "approved") {
        setSourceId(passage.source_id);
        setPassageId(passage.id);
      } else setError("Rules can only use a passage from an approved source version.");
    }
  }, [organizationId, passageIdFromUrl, sourceId]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setLoading(true);
      load().catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "Could not load the rules editor.")).finally(() => setLoading(false));
    }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  useEffect(() => {
    if (!sourceId) return;
    let cancelled = false;
    apiRequest<{ passages: Passage[] }>(`orgs/${organizationId}/sources/${sourceId}`).then((result) => { if (!cancelled) setPassages(result.passages); }).catch((cause: unknown) => { if (!cancelled) setError(cause instanceof Error ? cause.message : "Could not load source passages."); });
    return () => { cancelled = true; };
  }, [organizationId, sourceId]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const parameters: Record<string, unknown> = {};
    if (["offer_name", "banned_phrase", "required_disclaimer"].includes(ruleType)) parameters.value = form.get("value");
    if (ruleType === "discount_percent") parameters.percent = Number(form.get("percent"));
    if (ruleType === "valid_from" || ruleType === "valid_until") parameters.date = form.get("date");
    if (ruleType === "approved_logo") parameters.version = form.get("version");
    if (ruleType === "approved_logo") parameters.deprecated = form.get("deprecated") === "on";
    if (ruleType === "channel_length_limit") { parameters.channel = form.get("limit_channel"); parameters.max_characters = Number(form.get("max_characters")); }
    if (ruleType === "brand_colors") { parameters.colors = String(form.get("colors") ?? "").split(",").map((color) => color.trim()).filter(Boolean); parameters.tolerance_delta_e = Number(form.get("tolerance_delta_e") || 12); }
    if (ruleType === "typography") parameters.value = form.get("value");
    setError(""); setNotice(""); setBusy(true);
    try {
      await apiRequest<Rule>(`orgs/${organizationId}/rules`, { method: "POST", body: JSON.stringify({ rule_type: ruleType, parameters, channel: form.get("channel") || null, valid_from: form.get("valid_from") || null, valid_to: form.get("valid_to") || null, source_passage_id: passageId }) });
      setNotice(role === "admin" ? "Rule saved as active with its approved-source evidence." : "Rule submitted as a suggestion. An Admin must approve it before checks can use it.");
      formElement.reset();
      const updated = await apiRequest<Rule[]>(`orgs/${organizationId}/rules`); setRules(updated);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not save this rule."); }
    finally { setBusy(false); }
  }

  async function decide(ruleId: string, decision: "approve" | "reject") {
    setError("");
    try {
      await apiRequest<Rule>(`orgs/${organizationId}/rules/${ruleId}/decision`, { method: "POST", body: JSON.stringify({ decision }) });
      setRules(await apiRequest<Rule[]>(`orgs/${organizationId}/rules`));
      setNotice(`Suggestion ${decision === "approve" ? "approved" : "rejected"}.`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not review this rule suggestion."); }
  }

  const selectedPassage = passages.find((passage) => passage.id === passageId);

  return <>
    <header className="workspace-heading"><p className="eyebrow"><Link href={`/app/organisations/${organizationId}`}>Organisation</Link> / Rules</p><h1>Structured rules</h1><p>Rules record an exact check and the approved passage that supports it. Admin-created rules are active; Creator submissions stay suggestions until an Admin reviews them.</p></header>
    {error && <p className="auth-message auth-error" role="alert">{error}</p>}{notice && <p className="auth-message auth-success" role="status">{notice}</p>}
    {loading ? <div className="workspace-skeleton" aria-label="Loading rules"><div/><div/></div> : <>
      <section className="workspace-section"><p className="eyebrow">Rule editor</p><h2>Add evidence-backed rule</h2>{sources.length === 0 ? <p>Approve a source version first, then link each rule to one of its passages.</p> : <form className="rule-editor-form" onSubmit={submit}>
        <label className="form-field">Approved source<select value={sourceId} onChange={(event) => { setSourceId(event.target.value); setPassageId(""); }}>{sources.map((source) => <option value={source.id} key={source.id}>{source.title} · v{source.version}</option>)}</select></label>
        <label className="form-field">Evidence passage<select required value={passageId} onChange={(event) => setPassageId(event.target.value)}><option value="">Choose a passage</option>{passages.map((passage) => <option key={passage.id} value={passage.id}>{passage.location_label ?? `Page ${passage.page_number ?? "—"}`} · {passage.text.slice(0, 100)}</option>)}</select></label>
        {selectedPassage && <blockquote className="rule-evidence">{selectedPassage.text}<small>{selectedPassage.source_title} · v{selectedPassage.source_version} · {selectedPassage.location_label ?? "No page reference"}</small></blockquote>}
        <label className="form-field">Rule type<select value={ruleType} onChange={(event) => setRuleType(event.target.value as RuleType)}>{Object.entries(labels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        {["offer_name", "banned_phrase", "required_disclaimer"].includes(ruleType) && <label className="form-field">{labels[ruleType]}<input name="value" required maxLength={500}/></label>}
        {ruleType === "discount_percent" && <label className="form-field">Percent<input name="percent" type="number" min={0} max={100} step="0.01" required/></label>}
        {(ruleType === "valid_from" || ruleType === "valid_until") && <label className="form-field">Date<input name="date" type="date" required/></label>}
        {ruleType === "approved_logo" && <><label className="form-field">Logo version<input name="version" required maxLength={80} placeholder="Primary lockup v2"/></label><label className="form-field"><span><input name="deprecated" type="checkbox"/> Deprecated logo version (flag if detected)</span></label></>}
        {ruleType === "brand_colors" && <><label className="form-field">Approved colours, comma-separated hex<input name="colors" required placeholder="#143D32, #F2B36D" pattern="\s*#[0-9a-fA-F]{6}(\s*,\s*#[0-9a-fA-F]{6})*\s*"/></label><label className="form-field">Delta E tolerance (CIEDE2000)<input name="tolerance_delta_e" type="number" min={1} max={100} defaultValue={12} required/></label></>}
        {ruleType === "typography" && <label className="form-field">Typography guidance<input name="value" required maxLength={500} placeholder="Use the approved sans-serif family for headings"/></label>}
        {ruleType === "channel_length_limit" && <><label className="form-field">Channel to limit<input name="limit_channel" required maxLength={50} placeholder="Instagram caption"/></label><label className="form-field">Maximum characters<input name="max_characters" type="number" min={1} max={100000} required/></label></>}
        <div className="rule-date-fields"><label className="form-field">Rule effective from<input name="valid_from" type="date"/></label><label className="form-field">Rule effective until<input name="valid_to" type="date"/></label></div>
        <label className="form-field">Applies to channel (optional)<input name="channel" maxLength={50}/></label>
        <button className="button button-primary" disabled={busy || !passageId}>{busy ? "Saving…" : role === "admin" ? "Save active rule" : "Submit rule suggestion"}</button>
      </form>}</section>
      <section className="workspace-section"><p className="eyebrow">Rule register</p><h2>Current rules and suggestions</h2>{rules.length === 0 ? <p>No rules have been recorded yet.</p> : <div className="rule-list">{rules.map((rule) => <article className="rule-row" key={rule.id}><div><p className="eyebrow">{rule.rule_type.replaceAll("_", " ")} · <span className={`status-label status-${rule.status}`}>{rule.status}</span></p><p>{Object.entries(rule.parameters).map(([key, value]) => `${key.replaceAll("_", " ")}: ${value}`).join(" · ")}</p><small>Evidence passage: <code>{rule.source_passage_id}</code>{rule.channel ? ` · ${rule.channel}` : ""}</small></div>{rule.status === "suggested" && role === "admin" && <div className="inline-actions"><button className="small-button" onClick={() => void decide(rule.id, "approve")}>Approve</button><button className="small-button" onClick={() => void decide(rule.id, "reject")}>Reject</button></div>}</article>)}</div>}</section>
    </>}
  </>;
}
