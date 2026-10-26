export const metadata = { title: "Workspace security", robots: { index: false, follow: false } };

export default function WorkspaceSecurityPage() {
  return <>
    <header className="workspace-heading"><p className="eyebrow">Workspace controls</p><h1>Security and AI processing</h1><p>Review what this phase stores and where content is processed.</p></header>
    <section className="security-ledger"><div><span>LLM vendor</span><strong>Mock only · no live vendor</strong><p>The mock judgement client returns insufficient evidence. It does not send source or asset text outside the service. Local hashed lexical vectors and perceptual image hashes are prototypes; campaign scans use deterministic rules and cross-asset comparisons.</p></div><div><span>Workspace permission</span><strong>Off by default</strong><p>Each organisation has a server-side AI-processing permission. The deployment must also enable a provider; this repository contains no live LLM adapter.</p></div><div><span>Secrets</span><strong>Server-side only</strong><p>API keys and storage credentials are read from environment variables. Session and invite secrets are stored as hashes.</p></div><div><span>Files</span><strong>Private storage provisioned</strong><p>Approved source documents and campaign assets are stored in private local or S3-compatible storage. Access requires organisation membership and a short-lived signed link.</p></div></section>
    <p className="security-disclaimer">These are implementation details for the current local phase. They are not a production security certification.</p>
  </>;
}
