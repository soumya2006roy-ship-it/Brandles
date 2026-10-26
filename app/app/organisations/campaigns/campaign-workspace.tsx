"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { apiRequest } from "@/app/lib/api-client";
import { PlatformPreview } from "./platform-preview";

type Asset = { id: string; asset_group_id: string; version: number; current: boolean; supersedes_asset_id: string | null; asset_type: string; channel: string; language: string; content_type: string; original_filename: string | null; sha256: string; size_bytes: number; malware_status: string; extraction_status: string; metadata_stripped: boolean; text_content: string | null; extracted_text: string | null; logo_matches: { source_id: string; source_title: string; source_version: number; logo_version: string; similarity: number; matched: boolean; method: string }[]; created_at: string };
type Campaign = { id: string; name: string; channels: string[]; starts_at: string | null; ends_at: string | null; language: string; status: string; assets: Asset[] };
type OrgSummary = { id: string; role: string };
type Scan = { id: string; campaign_id: string; status: string; requested_by: string; rules_version: string | null; created_at: string; completed_at: string | null; finding_count: number; progress: number; cancel_requested: boolean };
type Finding = { id: string; scan_id: string; asset_id: string | null; finding_type: string; severity: string; status: string; flagged_region: Record<string, unknown> | null; rule_id: string | null; source_passage_id: string | null; source_title: string | null; source_version: number | null; source_page_number: number | null; source_location_label: string | null; source_text: string | null; quoted_excerpt: string | null; confidence: number | null; suggested_fix: string | null; resolution: string | null; dismissal_reason: string | null };
type Fact = { id: string; asset_id: string; channel: string; fact_type: string; value: string; asset_location: Record<string, unknown> | null; source_passage_id: string | null };
type Review = { id: string; submission_id: string; campaign_id: string; campaign_name: string; asset_id: string; asset_version: number; decision: string; submitted_by_user_id: string | null; reviewer_user_id: string | null; comment: string | null; created_at: string };
type Rule = { id: string; rule_type: string; parameters: Record<string, unknown>; channel: string | null; valid_from: string | null; valid_to: string | null; status: string };

export function CampaignWorkspace({ organizationId, campaignId }: { organizationId: string; campaignId: string }) {
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [role, setRole] = useState("");
  const [replaceGroup, setReplaceGroup] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [scans, setScans] = useState<Scan[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [decisionText, setDecisionText] = useState<Record<string, string>>({});
  const [reviewComment, setReviewComment] = useState("");
  const [facts, setFacts] = useState<Fact[]>([]);
  const [filterSeverity, setFilterSeverity] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");
  const [filterType, setFilterType] = useState("all");
  const [filterChannel, setFilterChannel] = useState("all");
  const [reviewHistory, setReviewHistory] = useState<Review[]>([]);
  const [assetDrafts, setAssetDrafts] = useState<Record<string, string>>({});
  const [rules, setRules] = useState<Rule[]>([]);

  const load = useCallback(async () => {
    const [orgs, detail, scanRows, reviewRows, ruleRows] = await Promise.all([apiRequest<OrgSummary[]>("orgs"), apiRequest<Campaign>(`orgs/${organizationId}/campaigns/${campaignId}`), apiRequest<Scan[]>(`orgs/${organizationId}/campaigns/${campaignId}/scans`), apiRequest<Review[]>(`orgs/${organizationId}/campaigns/${campaignId}/reviews`), apiRequest<Rule[]>(`orgs/${organizationId}/rules?status=active`)]);
    setRole(orgs.find((org) => org.id === organizationId)?.role ?? "");
    setCampaign(detail);
    setScans(scanRows);
    setReviewHistory(reviewRows);
    setRules(ruleRows);
    const latest = scanRows[0];
    if (latest) {
      const rows = await apiRequest<Finding[]>(`orgs/${organizationId}/campaigns/${campaignId}/scans/${latest.id}/findings`);
      setFindings(rows);
      setFacts(latest.status === "completed" ? await apiRequest<Fact[]>(`orgs/${organizationId}/campaigns/${campaignId}/scans/${latest.id}/facts`) : []);
    } else { setFindings([]); setFacts([]); }
  }, [organizationId, campaignId]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      load().catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "Could not load this campaign.")).finally(() => setLoading(false));
    }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  useEffect(() => {
    const current = scans[0];
    if (!current || !["queued", "running"].includes(current.status)) return;
    const timer = window.setInterval(() => {
      apiRequest<Scan>(`orgs/${organizationId}/campaigns/${campaignId}/scans/${current.id}`).then((updated) => {
        setScans((items) => items.map((item) => item.id === updated.id ? updated : item));
        if (!["queued", "running"].includes(updated.status)) void load();
      }).catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "Could not refresh scan status."));
    }, 2000);
    return () => window.clearInterval(timer);
  }, [scans, organizationId, campaignId, load]);

  const assetGroups = useMemo(() => {
    const groups = new Map<string, Asset[]>();
    for (const asset of campaign?.assets ?? []) groups.set(asset.asset_group_id, [...(groups.get(asset.asset_group_id) ?? []), asset]);
    return [...groups.values()].map((versions) => versions.sort((a, b) => b.version - a.version));
  }, [campaign]);
  const filteredFindings = useMemo(() => findings.filter((finding) => {
    const channel = campaign?.assets.find((asset) => asset.id === finding.asset_id)?.channel ?? "campaign";
    return (filterSeverity === "all" || finding.severity === filterSeverity) && (filterStatus === "all" || finding.status === filterStatus) && (filterType === "all" || finding.finding_type === filterType) && (filterChannel === "all" || channel === filterChannel);
  }), [findings, campaign, filterSeverity, filterStatus, filterType, filterChannel]);
  const groupedFindings = useMemo(() => {
    const groups = new Map<string, Finding[]>();
    for (const finding of filteredFindings) groups.set(finding.asset_id ?? "campaign", [...(groups.get(finding.asset_id ?? "campaign") ?? []), finding]);
    return [...groups.entries()];
  }, [filteredFindings]);

  async function addAsset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const body = new FormData(formElement);
    const file = body.get("file");
    if (file instanceof File && file.size === 0) body.delete("file");
    if (replaceGroup) body.set("asset_group_id", replaceGroup); else body.delete("asset_group_id");
    setError(""); setNotice(""); setBusy(true);
    try {
      const result = await apiRequest<Asset>(`orgs/${organizationId}/campaigns/${campaignId}/assets`, { method: "POST", body });
      setNotice(`Asset version ${result.version} saved. Any scans of the replaced version are marked stale.`);
      setReplaceGroup("");
      formElement.reset();
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not save this campaign asset."); }
    finally { setBusy(false); }
  }

  async function download(asset: Asset) {
    try {
      const result = await apiRequest<{ url: string }>(`orgs/${organizationId}/campaigns/${campaignId}/assets/${asset.id}/download`);
      window.open(result.url, "_blank", "noopener,noreferrer");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not open this asset file."); }
  }

  async function startScan() {
    setError(""); setNotice(""); setBusy(true);
    try {
      await apiRequest<Scan>(`orgs/${organizationId}/campaigns/${campaignId}/scans`, { method: "POST" });
      setNotice("Campaign scan queued. Findings will appear when the workspace worker completes it.");
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not queue a campaign scan."); }
    finally { setBusy(false); }
  }

  async function decideFinding(finding: Finding, decision: "resolve" | "dismiss") {
    const text = (decisionText[finding.id] ?? "").trim();
    if (!text) { setError(decision === "dismiss" ? "Enter a reason before dismissing a finding." : "Describe the edit or resolution before closing a finding."); return; }
    setError(""); setNotice("");
    try {
      await apiRequest<Finding>(`orgs/${organizationId}/campaigns/${campaignId}/findings/${finding.id}/decision`, { method: "POST", body: JSON.stringify(decision === "dismiss" ? { decision, dismissal_reason: text } : { decision, resolution: text }) });
      await load(); setNotice(decision === "dismiss" ? "Finding dismissed with a reason." : "Finding resolved.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not update this finding."); }
  }

  async function requestClarification(finding: Finding) {
    const question = (decisionText[finding.id] ?? "").trim();
    if (question.length < 5) { setError("Enter a question with at least five characters."); return; }
    setError("");
    try {
      await apiRequest<Finding>(`orgs/${organizationId}/campaigns/${campaignId}/findings/${finding.id}/clarification`, { method: "POST", body: JSON.stringify({ question }) });
      await load(); setNotice("Clarification requested from an organisation Admin.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not request clarification."); }
  }

  async function saveEditedVersion(finding: Finding) {
    const asset = campaign?.assets.find((item) => item.id === finding.asset_id);
    const editedText = assetDrafts[finding.id]?.trim();
    if (!asset || asset.asset_type !== "text" || !editedText) { setError("Enter the edited text to create a new asset version."); return; }
    const body = new FormData(); body.set("channel", asset.channel); body.set("language", asset.language); body.set("asset_group_id", asset.asset_group_id); body.set("text_content", editedText);
    setError(""); setNotice(""); setBusy(true);
    try {
      const updated = await apiRequest<Asset>(`orgs/${organizationId}/campaigns/${campaignId}/assets`, { method: "POST", body });
      await load(); setNotice(`Edited text saved as asset version ${updated.version}. Run a fresh scan before review.`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not save a new asset version."); }
    finally { setBusy(false); }
  }

  async function acceptSuggestedFix(finding: Finding) {
    const asset = campaign?.assets.find((item) => item.id === finding.asset_id);
    const flagged = typeof finding.flagged_region?.text === "string" ? finding.flagged_region.text : "";
    if (!asset || asset.asset_type !== "text" || !flagged || !finding.suggested_fix) { setError("This suggestion cannot be applied as a direct text replacement. Edit the asset manually."); return; }
    const original = assetDrafts[finding.id] ?? asset.text_content ?? asset.extracted_text ?? "";
    if (!original.includes(flagged)) { setError("The flagged text is no longer present. Review the current asset version and edit it manually."); return; }
    const body = new FormData(); body.set("channel", asset.channel); body.set("language", asset.language); body.set("asset_group_id", asset.asset_group_id); body.set("text_content", original.replace(flagged, finding.suggested_fix));
    setError(""); setNotice(""); setBusy(true);
    try {
      const updated = await apiRequest<Asset>(`orgs/${organizationId}/campaigns/${campaignId}/assets`, { method: "POST", body });
      await load(); setNotice(`Suggested fix saved as asset version ${updated.version}. Run a fresh scan before review.`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not save the suggested fix as a new version."); }
    finally { setBusy(false); }
  }

  async function submitCampaignForReview() {
    if (!scans[0]) return;
    setError(""); setNotice(""); setBusy(true);
    try {
      await apiRequest<Review[]>(`orgs/${organizationId}/campaigns/${campaignId}/submit`, { method: "POST", body: JSON.stringify({ scan_id: scans[0].id, comment: reviewComment || null }) });
      await load(); setNotice("Campaign submitted to the Reviewer queue. The submission records current asset versions and scan evidence.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not submit this campaign for review."); }
    finally { setBusy(false); }
  }

  async function scanAction(action: "cancel" | "resume") {
    if (!scans[0]) return;
    setError("");
    try { await apiRequest<Scan>(`orgs/${organizationId}/campaigns/${campaignId}/scans/${scans[0].id}/${action}`, { method: "POST" }); await load(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : `Could not ${action} this scan.`); }
  }

  if (loading) return <div className="workspace-skeleton" aria-label="Loading campaign"><div/><div/><div/></div>;
  if (!campaign) return <p className="auth-message auth-error" role="alert">{error || "Campaign not found."}</p>;

  return <>
    <header className="workspace-heading"><p className="eyebrow"><Link href={`/app/organisations/${organizationId}/campaigns`}>Campaigns</Link> / {campaign.status}</p><h1>{campaign.name}</h1><p>{campaign.channels.join(" · ")} · {campaign.language} · {campaign.starts_at ?? "No start"} – {campaign.ends_at ?? "No end"}</p></header>
    {error && <p className="auth-message auth-error" role="alert">{error}</p>}{notice && <p className="auth-message auth-success" role="status">{notice}</p>}
    {(role === "admin" || role === "creator") && <section className="workspace-section"><p className="eyebrow">Channel asset</p><h2>Add or replace an asset version</h2><p>Upload a PDF, DOCX, UTF-8 text, PNG, JPEG, or WebP file, or paste caption/email/post text. File type is determined from its contents. Configured malware scanning fails closed; image metadata is stripped before private storage.</p><form className="asset-upload-form" onSubmit={addAsset}>
      <label className="form-field">Channel<select name="channel" required>{campaign.channels.map((channel) => <option key={channel}>{channel}</option>)}</select></label>
      <label className="form-field">Language<input name="language" defaultValue={campaign.language} maxLength={32} required/></label>
      <label className="form-field">Replace existing asset<select value={replaceGroup} onChange={(event) => setReplaceGroup(event.target.value)}><option value="">Create a new asset</option>{assetGroups.map((versions) => <option value={versions[0].asset_group_id} key={versions[0].asset_group_id}>{versions[0].channel} · {versions[0].original_filename ?? versions[0].extracted_text?.slice(0, 45) ?? "Text asset"} · v{versions[0].version}</option>)}</select></label>
      <label className="form-field">Upload file<input name="file" type="file" accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.webp,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown,image/png,image/jpeg,image/webp"/></label>
      <label className="form-field">Or paste text<textarea name="text_content" rows={7} maxLength={200000} placeholder="Paste a caption, email, poster copy, or LinkedIn post"/></label>
      <button className="button button-primary" disabled={busy}>{busy ? "Saving asset…" : replaceGroup ? "Save new version" : "Add asset"}</button>
    </form></section>}

      <section className="workspace-section"><p className="eyebrow">Asset register</p><h2>Assets and versions</h2>{campaign.assets.length === 0 ? <div className="workspace-empty"><h3>No campaign assets yet</h3><p>Add one asset for every channel that needs review.</p></div> : <div className="asset-groups">{assetGroups.map((versions) => <article className="asset-group" key={versions[0].asset_group_id}><h3>{versions[0].channel} <small>· {versions[0].asset_type}</small></h3><ol>{versions.map((asset) => <li className="asset-version" key={asset.id}><div><p className="eyebrow">Version {asset.version} · {asset.current ? "Current" : "Superseded"} · {new Date(asset.created_at).toLocaleString()}</p><p>{asset.original_filename ?? `${asset.channel} text`} · {asset.language} · {(asset.size_bytes / 1024).toFixed(1)} KB</p><p className="asset-statuses"><span>Malware: {asset.malware_status.replaceAll("_", " ")}</span><span>Extraction: {asset.extraction_status.replaceAll("_", " ")}</span>{asset.metadata_stripped && <span>Image metadata stripped</span>}</p>{asset.original_filename && <button className="small-button" type="button" onClick={() => void download(asset)}>Download file</button>}{asset.extracted_text && <details><summary>Extracted text</summary><pre>{asset.extracted_text}</pre></details>}{asset.current && asset.asset_type === "text" && <PlatformPreview channel={asset.channel} text={asset.extracted_text ?? asset.text_content ?? ""} approvedCharacterLimit={(() => { const matching = rules.find((rule) => rule.rule_type === "channel_length_limit" && (!rule.channel || rule.channel.toLowerCase() === asset.channel.toLowerCase())); const limit = Number(matching?.parameters.max_characters ?? 0); return limit > 0 ? limit : undefined; })()}/> }{asset.logo_matches.length > 0 && <div className="logo-matches"><strong>Approved logo comparison</strong><ul>{asset.logo_matches.map((match) => <li key={match.source_id}>{match.source_title} v{match.source_version} · {match.logo_version}: {(match.similarity * 100).toFixed(0)}% similarity · {match.matched ? "match" : "not matched"} ({match.method})</li>)}</ul></div>}</div></li>)}</ol></article>)}</div>}</section>
      <section className="workspace-section">
        <p className="eyebrow">Evidence-based checks</p>
        <h2>Campaign scan</h2>
        <p>Scans compare current assets with active rules linked to approved, effective source passages. Cross-asset differences and unsupported facts need human verification. No live judgement model is connected, so unsupported claims are never labelled as breaches.</p>
        {(campaign.language.toLowerCase().startsWith("hi") || campaign.assets.some((asset) => asset.current && asset.language.toLowerCase().startsWith("hi"))) && <p className="workspace-notice"><strong>Hindi checker · rule based prototype:</strong> Hindi phrase checks and lexical retrieval are available, but language accuracy is limited and every result needs human review.</p>}
        {(role === "admin" || role === "creator") && <button className="button button-primary" type="button" onClick={() => void startScan()} disabled={busy || ["queued", "running"].includes(scans[0]?.status ?? "")}>{busy ? "Working…" : "Run campaign scan"}</button>}
        {scans.length === 0 ? <div className="workspace-empty"><p>No campaign scan has been run.</p></div> : <div className="scan-results">
          <p className="eyebrow">Latest scan · {scans[0].status} · {scans[0].progress}% · {scans[0].finding_count} findings · {new Date(scans[0].created_at).toLocaleString()}</p>
          {scans[0].status === "running" && (role === "admin" || role === "creator") && <button className="small-button" type="button" onClick={() => void scanAction("cancel")}>Cancel scan</button>}
          {["failed", "cancelled"].includes(scans[0].status) && (role === "admin" || role === "creator") && <button className="small-button" type="button" onClick={() => void scanAction("resume")}>Resume scan</button>}
          {scans[0].status === "failed" && <p role="status">Scan failed. Check that the workspace worker is available, then resume it.</p>}
          {scans[0].status === "completed" && findings.length === 0 && <div className="workspace-empty"><p>No findings were produced by the configured checks. This is not a certification.</p></div>}
          {facts.length > 0 && <section className="campaign-consistency-graph" aria-label="Campaign Consistency Graph"><p className="eyebrow">Campaign Consistency Graph</p><ul>{campaign.assets.filter((asset) => asset.current).map((asset) => <li key={asset.id}><strong>{asset.channel}</strong><ul>{facts.filter((fact) => fact.asset_id === asset.id).map((fact) => <li key={fact.id}>{fact.fact_type}: {fact.value} {fact.source_passage_id ? "· approved source linked" : "· no approved source linked"}</li>)}</ul></li>)}</ul><p>Facts are extracted with local rules; unmatched facts are shown for people to verify.</p></section>}
          <div className="finding-filters">
            <label className="form-field">Severity<select value={filterSeverity} onChange={(event) => setFilterSeverity(event.target.value)}><option value="all">All</option>{["critical", "high", "medium", "low", "warning", "info"].map((value) => <option key={value}>{value}</option>)}</select></label>
            <label className="form-field">Status<select value={filterStatus} onChange={(event) => setFilterStatus(event.target.value)}><option value="all">All</option>{["open", "clarification_requested", "resolved", "dismissed", "stale"].map((value) => <option key={value}>{value.replaceAll("_", " ")}</option>)}</select></label>
            <label className="form-field">Finding type<select value={filterType} onChange={(event) => setFilterType(event.target.value)}><option value="all">All</option>{[...new Set(findings.map((finding) => finding.finding_type))].map((value) => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</select></label>
            <label className="form-field">Channel<select value={filterChannel} onChange={(event) => setFilterChannel(event.target.value)}><option value="all">All</option>{campaign.channels.map((value) => <option key={value}>{value}</option>)}</select></label>
          </div>
          {findings.length > 0 && groupedFindings.length === 0 && <div className="workspace-empty"><p>No findings match these filters.</p></div>}
          <div className="finding-list">
            {groupedFindings.map(([assetId, rows]) => <section key={assetId}>
              <h3>{assetId === "campaign" ? "Campaign findings" : `${campaign.assets.find((asset) => asset.id === assetId)?.channel ?? "Asset"} asset`}</h3>
              {rows.map((finding) => <article className="finding-card" key={finding.id}>
                <p className="eyebrow">{finding.finding_type.replaceAll("_", " ")} · {finding.severity} · {finding.status.replaceAll("_", " ")}</p>
                <h4>{finding.finding_type === "campaign_fact_conflict" ? "Review a cross-asset difference" : "Evidence-backed check"}</h4>
                {typeof finding.flagged_region?.text === "string" && <p><strong>Flagged text:</strong> “{finding.flagged_region.text}”</p>}
                {finding.finding_type === "campaign_fact_conflict" && <p><strong>Decision:</strong> Needs human verification. Differences alone are not treated as a breach.</p>}
                {finding.source_title && <details className="evidence-map"><summary>Evidence map · {finding.source_title} v{finding.source_version}</summary><blockquote className="rule-evidence">{finding.source_text || finding.quoted_excerpt}<small>Source {finding.source_title} · version {finding.source_version} · {finding.source_page_number ? `page ${finding.source_page_number}` : finding.source_location_label ?? "location not available"} · passage ID {finding.source_passage_id}</small></blockquote></details>}
                {Array.isArray(finding.flagged_region?.conflicting_assets) && <ul>{(finding.flagged_region.conflicting_assets as { asset_id: string; channel: string; value: string; excerpt: string }[]).map((other) => <li key={`${other.asset_id}-${other.value}`}><strong>{other.channel}:</strong> {other.value} · “{other.excerpt}”</li>)}</ul>}
                {!finding.source_title && finding.quoted_excerpt && <blockquote className="rule-evidence">{finding.quoted_excerpt}<small>Comparison excerpt from another campaign asset</small></blockquote>}
                {finding.confidence !== null && <p>Confidence: {(finding.confidence * 100).toFixed(0)}%</p>}
                {finding.suggested_fix && <p><strong>Suggested next step:</strong> {finding.suggested_fix}</p>}
                {finding.suggested_fix && typeof finding.flagged_region?.text === "string" && <div className="suggestion-diff" aria-label="Original text compared with suggested fix"><p><strong>Original:</strong> <del>{finding.flagged_region.text}</del></p><p><strong>Suggested:</strong> <ins>{finding.suggested_fix}</ins></p></div>}
                {finding.status === "open" && (role === "admin" || role === "creator") && <div className="finding-decision">
                  <label className="form-field">Resolution or dismissal reason<input value={decisionText[finding.id] ?? ""} onChange={(event) => setDecisionText((state) => ({ ...state, [finding.id]: event.target.value }))} maxLength={2000} required/></label>
                  {campaign.assets.find((asset) => asset.id === finding.asset_id)?.asset_type === "text" && <>
                    <label className="form-field">Edited asset text<textarea rows={5} value={assetDrafts[finding.id] ?? campaign.assets.find((asset) => asset.id === finding.asset_id)?.text_content ?? ""} onChange={(event) => setAssetDrafts((state) => ({ ...state, [finding.id]: event.target.value }))}/></label>
                    {finding.suggested_fix && <button className="small-button" type="button" disabled={busy} onClick={() => void acceptSuggestedFix(finding)}>Accept fix and save a new version</button>}
                    <button className="small-button" type="button" disabled={busy} onClick={() => void saveEditedVersion(finding)}>Save as new asset version</button>
                  </>}
                  <div className="inline-actions"><button className="small-button" type="button" onClick={() => void decideFinding(finding, "resolve")}>Record resolution</button><button className="small-button" type="button" onClick={() => void decideFinding(finding, "dismiss")}>Dismiss with reason</button><button className="small-button" type="button" onClick={() => void requestClarification(finding)}>Request clarification</button></div>
                </div>}
                {finding.resolution && <p><strong>Resolution / clarification:</strong> {finding.resolution}</p>}
                {finding.dismissal_reason && <p><strong>Dismissal reason:</strong> {finding.dismissal_reason}</p>}
              </article>)}
            </section>)}
          </div>
        </div>}
      </section>
      {(role === "admin" || role === "creator") && scans[0]?.status === "completed" && !["in_review", "approved"].includes(campaign.status) && <section className="workspace-section"><p className="eyebrow">Submit for review</p><h2>Send these versions to a Reviewer</h2><p>Review is recorded against the exact asset versions and scan. High and Critical findings must be resolved or dismissed first.</p><label className="form-field">Submission note (optional)<input value={reviewComment} onChange={(event) => setReviewComment(event.target.value)} maxLength={1000}/></label><button className="button button-primary" type="button" onClick={() => void submitCampaignForReview()} disabled={busy || findings.some((finding) => finding.status === "open" && ["high", "critical"].includes(finding.severity))}>{busy ? "Submitting…" : "Submit for review"}</button></section>}
      {reviewHistory.length > 0 && <section className="workspace-section"><p className="eyebrow">Decision history</p><h2>Review record</h2><ul className="invite-list">{reviewHistory.map((review) => <li key={review.id}><div><strong>{review.decision.replaceAll("_", " ")} · asset version {review.asset_version}</strong><span>{review.campaign_name} · {review.reviewer_user_id ? "Reviewer decision" : "Submitted for review"} · {new Date(review.created_at).toLocaleString()}</span>{review.comment && <span>{review.comment}</span>}</div></li>)}</ul></section>}
  </>;
}
