"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { apiRequest } from "@/app/lib/api-client";

type Asset = { id: string; asset_group_id: string; version: number; current: boolean; supersedes_asset_id: string | null; asset_type: string; channel: string; language: string; content_type: string; original_filename: string | null; sha256: string; size_bytes: number; malware_status: string; extraction_status: string; metadata_stripped: boolean; text_content: string | null; extracted_text: string | null; logo_matches: { source_id: string; source_title: string; source_version: number; logo_version: string; similarity: number; matched: boolean; method: string }[]; created_at: string };
type Campaign = { id: string; name: string; channels: string[]; starts_at: string | null; ends_at: string | null; language: string; status: string; assets: Asset[] };
type OrgSummary = { id: string; role: string };

export function CampaignWorkspace({ organizationId, campaignId }: { organizationId: string; campaignId: string }) {
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [role, setRole] = useState("");
  const [replaceGroup, setReplaceGroup] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const [orgs, detail] = await Promise.all([apiRequest<OrgSummary[]>("orgs"), apiRequest<Campaign>(`orgs/${organizationId}/campaigns/${campaignId}`)]);
    setRole(orgs.find((org) => org.id === organizationId)?.role ?? "");
    setCampaign(detail);
  }, [organizationId, campaignId]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      load().catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "Could not load this campaign.")).finally(() => setLoading(false));
    }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  const assetGroups = useMemo(() => {
    const groups = new Map<string, Asset[]>();
    for (const asset of campaign?.assets ?? []) groups.set(asset.asset_group_id, [...(groups.get(asset.asset_group_id) ?? []), asset]);
    return [...groups.values()].map((versions) => versions.sort((a, b) => b.version - a.version));
  }, [campaign]);

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

      <section className="workspace-section"><p className="eyebrow">Asset register</p><h2>Assets and versions</h2>{campaign.assets.length === 0 ? <div className="workspace-empty"><h3>No campaign assets yet</h3><p>Add one asset for every channel that needs review.</p></div> : <div className="asset-groups">{assetGroups.map((versions) => <article className="asset-group" key={versions[0].asset_group_id}><h3>{versions[0].channel} <small>· {versions[0].asset_type}</small></h3><ol>{versions.map((asset) => <li className="asset-version" key={asset.id}><div><p className="eyebrow">Version {asset.version} · {asset.current ? "Current" : "Superseded"} · {new Date(asset.created_at).toLocaleString()}</p><p>{asset.original_filename ?? `${asset.channel} text`} · {asset.language} · {(asset.size_bytes / 1024).toFixed(1)} KB</p><p className="asset-statuses"><span>Malware: {asset.malware_status.replaceAll("_", " ")}</span><span>Extraction: {asset.extraction_status.replaceAll("_", " ")}</span>{asset.metadata_stripped && <span>Image metadata stripped</span>}</p>{asset.original_filename && <button className="small-button" type="button" onClick={() => void download(asset)}>Download file</button>}{asset.extracted_text && <details><summary>Extracted text</summary><pre>{asset.extracted_text}</pre></details>}{asset.logo_matches.length > 0 && <div className="logo-matches"><strong>Approved logo comparison</strong><ul>{asset.logo_matches.map((match) => <li key={match.source_id}>{match.source_title} v{match.source_version} · {match.logo_version}: {(match.similarity * 100).toFixed(0)}% similarity · {match.matched ? "match" : "not matched"} ({match.method})</li>)}</ul></div>}</div></li>)}</ol></article>)}</div>}</section>
  </>;
}
