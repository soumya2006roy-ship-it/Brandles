"use client";

import { useMemo, useState } from "react";
import { useToast } from "@/app/ui";

type FindingState = "open" | "accepted" | "edited" | "dismissed";
type Finding = { id: string; severity: "high" | "medium"; title: string; asset: string; original: string; suggested: string; citation: string; excerpt: string; confidence: number; state: FindingState; reason?: string; editedText?: string };

const initialFindings: Finding[] = [
  { id: "claim", severity: "high", title: "Unsupported product claim", asset: "Instagram post", original: "Our moisturiser cures acne in 24 hours.", suggested: "Our moisturiser helps to keep the skin hydrated.", citation: "Product Sheet · Approved wording · v3", excerpt: "“The moisturiser helps to keep the skin hydrated.”", confidence: 92, state: "open" },
  { id: "offer", severity: "high", title: "Offer does not match the approved discount", asset: "Promotional email", original: "Take 30% off your order.", suggested: "Take 20% off your order.", citation: "Offer Terms · Current promotion · v2", excerpt: "“Current offer: 20% off until 30 November.”", confidence: 99, state: "open" },
  { id: "campaign", severity: "medium", title: "Campaign discount mismatch", asset: "Campaign comparison", original: "Instagram: offer not stated · Email: 30% off", suggested: "Use the approved 20% offer in the campaign assets.", citation: "Campaign Consistency Graph · Offer comparison", excerpt: "Approved offer is 20%. The email asset states 30%; the poster does not carry the approved offer.", confidence: 97, state: "open" },
  { id: "logo", severity: "medium", title: "Poster uses a previous logo version", asset: "Campaign poster", original: "Logo file: brand-mark-final-2023.svg", suggested: "Replace with the current approved logo asset.", citation: "Brand Assets · Current logo · v4", excerpt: "The poster contains a logo marked as the previous version. Use the current approved logo file.", confidence: 88, state: "open" },
];

export function DemoExperience() {
  const [scanned, setScanned] = useState(false);
  const [findings, setFindings] = useState(initialFindings);
  const [sourceId, setSourceId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");
  const [dismissId, setDismissId] = useState<string | null>(null);
  const [dismissReason, setDismissReason] = useState("");
  const [rescanComplete, setRescanComplete] = useState(false);
  const [reviewerName, setReviewerName] = useState("");
  const [approval, setApproval] = useState<{ name: string; version: string; timestamp: string } | null>(null);
  const notify = useToast();
  const openCount = useMemo(() => findings.filter((finding) => finding.state === "open").length, [findings]);
  const selectedSource = findings.find((finding) => finding.id === sourceId);

  function updateFinding(id: string, change: Partial<Finding>) {
    setFindings((current) => current.map((finding) => finding.id === id ? { ...finding, ...change } : finding));
    setRescanComplete(false);
    setApproval(null);
  }
  function runScan() {
    setScanned(true);
    setRescanComplete(false);
    setApproval(null);
    notify("Scan complete. Four seeded findings are ready to review.", "success");
  }
  function saveDismissal() {
    if (!dismissReason.trim()) return;
    updateFinding(dismissId!, { state: "dismissed", reason: dismissReason.trim() });
    setDismissId(null);
    setDismissReason("");
    notify("Dismissal reason recorded.", "info");
  }
  function rescan() {
    if (openCount > 0) return;
    setRescanComplete(true);
    setApproval(null);
    notify("Rescan complete. No unresolved seeded findings remain.", "success");
  }
  function approve() {
    if (!reviewerName.trim() || !rescanComplete) return;
    setApproval({ name: reviewerName.trim(), version: "Campaign v2", timestamp: new Date().toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) });
    notify("Reviewer approval recorded for Campaign v2.", "success");
  }

  return <section className="demo-workspace" aria-labelledby="demo-workspace-title">
    <div className="demo-workspace-top"><div><p className="eyebrow">CAMPAIGN WORKSPACE · SKINCARE OFFER</p><h2 id="demo-workspace-title">Hydration campaign · November</h2></div><span className="simulation-badge"><i/> Simulation</span></div>
    <div className="demo-overview"><div><span>ASSETS</span><strong>03</strong></div><div><span>FINDINGS</span><strong>{scanned ? "04" : "—"}</strong></div><div><span>OPEN</span><strong className={openCount ? "text-danger" : ""}>{scanned ? String(openCount).padStart(2, "0") : "—"}</strong></div><div><span>STATUS</span><strong className="demo-status">{approval ? "Approved" : rescanComplete ? "Ready" : scanned ? "In review" : "Draft"}</strong></div></div>

    {!scanned ? <div className="demo-empty"><div className="empty-icon">◎</div><h3>Ready to check the campaign</h3><p>Three seeded assets are waiting for a pre-publication scan: an Instagram post, a promotional email and a campaign poster.</p><button className="button button-primary" type="button" onClick={runScan}>Run scan <span aria-hidden="true">→</span></button></div> : <>
      <div className="demo-findings-header"><div><p className="eyebrow">04 FINDINGS · SOURCE-LINKED</p><h3>Review each flag, then rescan.</h3></div><span className="demo-confidence-note">Confidence is a seeded demo value</span></div>
      <div className="demo-assets"><div className="asset-strip"><span>CAMPAIGN ASSETS</span><div><span className="asset-chip">Instagram post</span><span className="asset-chip">Email</span><span className="asset-chip">Poster</span></div></div>
        {findings.map((finding) => <article className={`finding-card ${finding.state !== "open" ? "finding-resolved" : ""}`} key={finding.id}>
          <div className="finding-card-heading"><span className={`severity-badge severity-${finding.severity}`}>{finding.severity === "high" ? "High" : "Medium"}</span><span className="finding-asset-label">{finding.asset}</span><span className={`finding-state state-${finding.state}`}>{finding.state === "open" ? "Open" : finding.state === "dismissed" ? "Dismissed · reason saved" : "Resolved · " + finding.state}</span></div>
          <h4>{finding.title}</h4>
          <div className="finding-columns"><div className="finding-column original-column"><span className="mini-label">ORIGINAL</span><p>{finding.id === "claim" ? <><button className="text-highlight highlight-danger" type="button" onClick={() => setSourceId(finding.id)}>cures acne in 24 hours</button></> : finding.id === "offer" ? <>Take <button className="text-highlight highlight-danger" type="button" onClick={() => setSourceId(finding.id)}>30% off</button> your order.</> : finding.id === "campaign" ? <><button className="text-highlight highlight-warning" type="button" onClick={() => setSourceId(finding.id)}>Instagram: offer not stated · Email: 30% off</button></> : <>Logo file: <button className="text-highlight highlight-warning" type="button" onClick={() => setSourceId(finding.id)}>brand-mark-final-2023.svg</button></>}</p></div><div className="finding-column suggested-column"><span className="mini-label">SUGGESTED FIX</span>{editingId === finding.id ? <><textarea className="edit-textarea" value={editText} onChange={(event) => setEditText(event.target.value)} aria-label={`Edit suggested fix for ${finding.title}`}/><div className="row-actions"><button className="small-button small-primary" type="button" onClick={() => { updateFinding(finding.id, { state: "edited", editedText: editText }); setEditingId(null); notify("Edited suggestion saved.", "success"); }}>Save edit</button><button className="small-button" type="button" onClick={() => setEditingId(null)}>Cancel</button></div></> : <><p>{finding.editedText ?? finding.suggested}</p><button className="source-link" type="button" onClick={() => setSourceId(finding.id)}>View approved passage ↗</button></>}</div></div>
          <div className="finding-footer"><span>{finding.citation} <span className="citation-sep">·</span> {finding.confidence}% confidence</span>{finding.state === "open" && <div className="row-actions"><button className="small-button small-primary" type="button" onClick={() => { updateFinding(finding.id, { state: "accepted" }); notify("Suggested fix accepted.", "success"); }}>Accept</button><button className="small-button" type="button" onClick={() => { setEditingId(finding.id); setEditText(finding.suggested); }}>Edit</button><button className="small-button small-danger" type="button" onClick={() => { setDismissId(finding.id); setDismissReason(""); }}>Dismiss</button></div>}</div>
          {dismissId === finding.id && <div className="dismiss-panel"><label htmlFor={`reason-${finding.id}`}>Reason for dismissing <span aria-hidden="true">*</span></label><div className="dismiss-row"><input id={`reason-${finding.id}`} required value={dismissReason} onChange={(event) => setDismissReason(event.target.value)} placeholder="Explain why this finding does not apply"/><button className="small-button small-primary" type="button" disabled={!dismissReason.trim()} onClick={saveDismissal}>Save reason</button><button className="small-button" type="button" onClick={() => setDismissId(null)}>Cancel</button></div></div>}
        </article>)}
      </div>
      {selectedSource && <div className="source-drawer" role="dialog" aria-modal="true" aria-labelledby="source-title"><div className="source-drawer-heading"><div><p className="eyebrow">APPROVED EVIDENCE · {selectedSource.citation}</p><h3 id="source-title">Passage behind this finding</h3></div><button className="close-button" type="button" onClick={() => setSourceId(null)} aria-label="Close approved passage">×</button></div><blockquote>{selectedSource.excerpt}</blockquote><p className="source-footnote">This seeded passage is shown as the approved source for the simulation.</p><button className="small-button" type="button" onClick={() => setSourceId(null)}>Close passage</button></div>}
      {rescanComplete && <div className="rescan-banner" role="status"><span className="success-mark">✓</span><div><strong>Rescan complete</strong><p>No unresolved seeded findings remain. A reviewer can now record a decision.</p></div></div>}
      <div className="demo-next-step"><div><p className="eyebrow">NEXT · RESCAN</p><p>{openCount ? `Resolve the remaining ${openCount} open finding${openCount === 1 ? "" : "s"} to continue.` : "All findings are handled. Run a rescan before reviewer approval."}</p></div><button className="button button-primary" type="button" onClick={rescan} disabled={openCount > 0}>Rescan campaign <span aria-hidden="true">↻</span></button></div>
      {rescanComplete && <div className="approval-panel"><div><p className="eyebrow">REVIEWER APPROVAL</p><h3>Record the human decision.</h3><p>Approval stores the reviewer’s name, campaign version and local timestamp.</p></div><div className="approval-controls"><label htmlFor="reviewer-name">Reviewer name</label><div className="approval-row"><input id="reviewer-name" value={reviewerName} onChange={(event) => setReviewerName(event.target.value)} placeholder="Enter reviewer name"/><button className="button button-primary" type="button" disabled={!reviewerName.trim()} onClick={approve}>Approve campaign <span aria-hidden="true">✓</span></button></div></div></div>}
      {approval && <div className="approval-record" role="status"><span className="success-mark">✓</span><div><strong>Approved by {approval.name}</strong><p>{approval.version} · {approval.timestamp} · Recorded in this browser for this simulation</p></div></div>}
      <button className="reset-demo" type="button" onClick={() => { setScanned(false); setFindings(initialFindings); setRescanComplete(false); setApproval(null); setSourceId(null); notify("Simulation reset to its seeded starting state.", "info"); }}>Reset simulation</button>
    </>}
    <p className="demo-disclaimer">Prototype notice: the Hindi checker and platform previews are simple rule-based prototypes. The demo findings above are seeded and do not come from an AI model.</p>
  </section>;
}
