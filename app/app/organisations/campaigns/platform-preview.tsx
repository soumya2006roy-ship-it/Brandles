"use client";

export function PlatformPreview({ channel, text, approvedCharacterLimit }: { channel: string; text: string; approvedCharacterLimit?: number }) {
  const hashtags = text.match(/#[\p{L}\p{N}_]+/gu) ?? [];
  const links = text.match(/https?:\/\/[^\s]+/giu) ?? [];
  const visible = approvedCharacterLimit && approvedCharacterLimit > 0 ? text.slice(0, approvedCharacterLimit) : text;
  const truncated = visible.length < text.length;
  return <aside className="platform-preview" aria-label={`${channel} style content preview`}>
    <p className="eyebrow">{channel} style layout · rule based preview prototype</p>
    <div className="platform-preview-card"><p>{visible || "Add text to preview this asset."}</p>{truncated && <p className="preview-truncation">Preview truncated at the approved {approvedCharacterLimit} character rule. Actual platform rendering may differ.</p>}</div>
    <p className="field-help">{text.length} characters · {hashtags.length} hashtags · {links.length} links{approvedCharacterLimit ? ` · ${approvedCharacterLimit} character rule` : " · no approved character limit rule"}. This does not post to a platform.</p>
  </aside>;
}
