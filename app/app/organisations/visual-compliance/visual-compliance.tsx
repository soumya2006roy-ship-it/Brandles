"use client";

import Link from "next/link";
import Image from "next/image";
import { useCallback, useEffect, useMemo, useState, type ChangeEvent, type DragEvent, type FormEvent } from "react";
import { apiRequest, apiUpload } from "@/app/lib/api-client";

type Campaign = { id: string; name: string; channels: string[] };
type Scan = { id: string; status: string; progress: number; finding_count: number; completed_at: string | null };
type Asset = { id: string; version: number; channel: string; original_filename: string | null; extracted_text: string | null; extraction_status: string };
type Finding = { id: string; asset_id: string | null; finding_type: string; severity: string; status: string; flagged_region: Record<string, unknown> | null; source_title: string | null; source_version: number | null; source_page_number: number | null; source_location_label: string | null; source_text: string | null; confidence: number | null; suggested_fix: string | null };
type VisualSubmission = { asset: Asset; scan: Scan; maturity: string };
type Fact = { fact_type: string; value: string; asset_location: Record<string, unknown> | null; asset_id: string };
const MAX_VISUAL_FILE_BYTES = 25 * 1024 * 1024;
function message(cause: unknown) { return cause instanceof Error ? cause.message : "Something went wrong. Please try again."; }

export function VisualCompliance({ organizationId }: { organizationId: string }) {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [campaignId, setCampaignId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [channel, setChannel] = useState("");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [submission, setSubmission] = useState<VisualSubmission | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [facts, setFacts] = useState<Fact[]>([]);
  const [selected, setSelected] = useState("");
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const campaign = useMemo(() => campaigns.find((item) => item.id === campaignId) ?? null, [campaigns, campaignId]);

  useEffect(() => {
    let active = true;
    apiRequest<Campaign[]>(`orgs/${organizationId}/campaigns`).then((rows) => { if (active) { setCampaigns(rows); setCampaignId(rows[0]?.id ?? ""); setChannel(rows[0]?.channels[0] ?? ""); } }).catch((cause) => { if (active) setError(message(cause)); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [organizationId]);

  const loadResult = useCallback(async (scan: Scan, activeCampaignId: string, activeAssetId: string) => {
    const [updated, rows, checkFacts] = await Promise.all([
      apiRequest<Scan>(`orgs/${organizationId}/campaigns/${activeCampaignId}/scans/${scan.id}`),
      apiRequest<Finding[]>(`orgs/${organizationId}/campaigns/${activeCampaignId}/scans/${scan.id}/findings`),
      apiRequest<Fact[]>(`orgs/${organizationId}/campaigns/${activeCampaignId}/scans/${scan.id}/facts`),
    ]);
    setSubmission((current) => current?.scan.id === updated.id ? { ...current, scan: updated } : current);
    setFindings(rows.filter((finding) => finding.asset_id === activeAssetId && (finding.finding_type.includes("logo") || finding.finding_type.includes("color") || finding.finding_type.includes("disclaimer"))));
    setFacts(checkFacts.filter((fact) => fact.asset_id === activeAssetId && fact.fact_type.startsWith("visual_")));
    if (updated.status === "failed") setError("The scan failed. Check the worker service and retry from the campaign page.");
  }, [organizationId]);

  useEffect(() => {
    if (!submission || !["queued", "running"].includes(submission.scan.status)) return;
    let active = true;
    const timer = window.setInterval(() => {
      void loadResult(submission.scan, campaignId, submission.asset.id).catch((cause) => { if (active) setError(message(cause)); });
    }, 2000);
    return () => { active = false; window.clearInterval(timer); };
  }, [submission, campaignId, loadResult]);

  const selectedFinding = useMemo(() => findings.find((item) => item.id === selected) ?? null, [findings, selected]);

  function chooseFile(next: File | null) {
    if (preview) URL.revokeObjectURL(preview);
    setPreview(next && next.size <= MAX_VISUAL_FILE_BYTES ? URL.createObjectURL(next) : "");
    setFile(next); setFindings([]); setFacts([]); setSubmission(null); setError(""); setNotice("");
    if (next && next.size > MAX_VISUAL_FILE_BYTES) setError("Choose an image that is 25 MB or smaller.");
  }
  function onFileChange(event: ChangeEvent<HTMLInputElement>) { chooseFile(event.target.files?.[0] ?? null); }
  function onDrop(event: DragEvent<HTMLLabelElement>) { event.preventDefault(); chooseFile(event.dataTransfer.files[0] ?? null); }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!campaign || !file) return;
    if (file.size > MAX_VISUAL_FILE_BYTES) { setError("Choose an image that is 25 MB or smaller."); return; }
    setBusy(true); setProgress(0); setError(""); setNotice("");
    try {
      const body = new FormData(); body.set("file", file); body.set("channel", channel); body.set("language", "en");
      const result = await apiUpload<VisualSubmission>(`orgs/${organizationId}/campaigns/${campaign.id}/visual-check`, body, setProgress);
      setSubmission(result); setNotice(`Image saved as asset version ${result.asset.version}. The visual scan is queued.`);
      if (!["queued", "running"].includes(result.scan.status)) await loadResult(result.scan, campaign.id, result.asset.id);
    } catch (cause) { setError(message(cause)); }
    finally { setBusy(false); }
  }

  async function decide(finding: Finding, decision: "resolve" | "dismiss" | "false-positive") {
    const reason = reasons[finding.id]?.trim() ?? "";
    if (!reason) { setError(decision === "resolve" ? "Describe what you changed before resolving." : "Add a reason before dismissing or flagging a false positive."); return; }
    if (!campaign || !submission) return;
    setError("");
    try {
      const payload = decision === "resolve" ? { decision: "resolve", resolution: reason } : { decision: "dismiss", dismissal_reason: decision === "false-positive" ? `False positive: ${reason}` : reason };
      await apiRequest(`orgs/${organizationId}/campaigns/${campaign.id}/findings/${finding.id}/decision`, { method: "POST", body: JSON.stringify(payload) });
      await loadResult(submission.scan, campaign.id, submission.asset.id);
      setNotice(decision === "false-positive" ? "False positive recorded in the campaign findings." : decision === "dismiss" ? "Finding dismissed with your reason." : "Finding resolution recorded.");
    } catch (cause) { setError(message(cause)); }
  }

  return <>
    <header className="workspace-heading"><p className="eyebrow"><Link href={`/app/organisations/${organizationId}`}>Workspace</Link> / Visual compliance</p><h1>Visual Compliance</h1><p>Check campaign artwork against approved colour, logo and disclaimer guidance. Local visual checks are a prototype, not an automated brand certification.</p></header>
    {error && <p className="auth-message auth-error" role="alert">{error}</p>}{notice && <p className="auth-message auth-success" role="status">{notice}</p>}
    {loading ? <section className="workspace-section" aria-live="polite"><p>Loading campaigns…</p><div className="workspace-skeleton"><div/><div/></div></section> : campaigns.length === 0 ? <section className="workspace-empty"><h2>Create a campaign first</h2><p>Visual checks attach the uploaded image to a campaign, scan, evidence and review history.</p><Link className="button button-primary" href={`/app/organisations/${organizationId}/campaigns`}>Open campaigns</Link></section> : <>
      <form className="workspace-section visual-upload" onSubmit={upload}>
        <p className="eyebrow">New visual scan</p><h2>Upload campaign artwork</h2>
        <label className="form-field">Campaign<select value={campaignId} onChange={(event) => { const id = event.target.value; setCampaignId(id); setChannel(campaigns.find((item) => item.id === id)?.channels[0] ?? ""); }} required>{campaigns.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label>
        <label className="form-field">Channel<select value={channel} onChange={(event) => setChannel(event.target.value)} required>{campaign?.channels.map((value) => <option key={value}>{value}</option>)}</select></label>
        <label className="visual-drop" onDragOver={(event) => event.preventDefault()} onDrop={onDrop}>
          <span><strong>{file ? file.name : "Drop an image here or choose a file"}</strong><small>PNG, JPEG or WebP · up to 25 MB · content is verified by the API</small></span>
          <input type="file" accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp" onChange={onFileChange} required/>
        </label>
        {file && <div className="visual-image-preview">{preview && <Image src={preview} alt={`Preview of ${file.name}`} width={960} height={640} unoptimized/>}<button type="button" className="small-button" onClick={() => chooseFile(null)}>Remove image</button></div>}
        {busy && <div className="visual-upload-progress" role="status"><span>Uploading and queueing scan · {progress}%</span><progress value={progress} max="100">{progress}%</progress></div>}
        <button type="submit" className="button button-primary" disabled={busy || !file || !campaignId}>{busy ? "Uploading…" : "Upload and scan image"}</button>
      </form>
      {submission && <section className="workspace-section visual-results" aria-live="polite"><div className="analytics-section-heading"><div><p className="eyebrow">Scan · {submission.scan.status} · {submission.scan.progress}%</p><h2>Visual findings</h2></div><span>{submission.scan.finding_count} total campaign findings</span></div>
        {submission.scan.status !== "completed" ? <p>{submission.scan.status === "failed" ? "Scan failed. See the error above or open the campaign to retry." : "The campaign worker is checking the image and its evidence."}</p> : <>
          <p className="visual-maturity">{submission.maturity}</p>
          <div className="visual-result-grid"><div className="visual-canvas">{preview && <Image src={preview} alt="Uploaded campaign artwork with finding overlays" width={1000} height={1000} unoptimized/>}{findings.map((finding) => { const box = finding.flagged_region?.bounding_box as { x: number; y: number; width: number; height: number } | null; return box ? <button key={finding.id} type="button" className={`visual-overlay severity-${finding.severity} ${selected === finding.id ? "is-selected" : ""}`} style={{ left: `${box.x * 100}%`, top: `${box.y * 100}%`, width: `${box.width * 100}%`, height: `${box.height * 100}%` }} aria-label={`Highlight ${finding.finding_type.replaceAll("_", " ")}`} onClick={() => setSelected(finding.id)}/> : null; })}</div>
            <div className="visual-finding-list"><h3>Findings</h3>{findings.length === 0 ? <p>No visual findings for the available checks. Typography and unconfigured checks can still be not verifiable.</p> : findings.map((finding) => <article key={finding.id} className={`visual-finding ${selected === finding.id ? "is-selected" : ""}`}><button type="button" className="visual-select-finding" onClick={() => setSelected(finding.id)}><span className="eyebrow">{finding.finding_type.replaceAll("_", " ")} · {finding.severity}</span><span>{String(finding.flagged_region?.explanation ?? finding.finding_type.replaceAll("_", " "))}</span><span>Confidence: {finding.confidence === null ? "not scored" : `${Math.round(finding.confidence * 100)}%`} · {finding.flagged_region?.needs_human_review ? "Needs human review" : "Rule signal"}</span></button>{finding.source_title && <details><summary>Evidence · {finding.source_title} v{finding.source_version}</summary><blockquote>{finding.source_text}<small>{finding.source_page_number ? `Page ${finding.source_page_number}` : finding.source_location_label ?? "Location not available"}</small></blockquote></details>}{finding.status === "open" && <div className="visual-actions"><label className="form-field">Resolution or dismissal reason<textarea rows={2} maxLength={1000} value={reasons[finding.id] ?? ""} onChange={(event) => setReasons({ ...reasons, [finding.id]: event.target.value })}/></label><button type="button" className="small-button" onClick={() => void decide(finding, "resolve")}>Resolve</button><button type="button" className="small-button" onClick={() => void decide(finding, "dismiss")}>Dismiss</button><button type="button" className="small-button" onClick={() => void decide(finding, "false-positive")}>Flag false positive</button></div>}</article>)}</div></div>
          <div className="visual-check-summary"><h3>Check summary</h3>{facts.map((fact) => <article key={fact.fact_type}><strong>{fact.fact_type.replace("visual_", "").replaceAll("_", " ")}</strong><span>{fact.value.replaceAll("_", " ")}</span>{fact.asset_location && fact.fact_type === "visual_palette_status" && <details><summary>Palette comparison</summary><pre>{JSON.stringify(fact.asset_location, null, 2)}</pre></details>}</article>)}</div>
          {selectedFinding && <p className="sr-only" role="status">Selected {selectedFinding.finding_type.replaceAll("_", " ")}. {selectedFinding.source_title ? `Evidence from ${selectedFinding.source_title}, version ${selectedFinding.source_version}.` : "No approved passage is linked."}</p>}
        </>}
      </section>}
    </>}
  </>;
}
