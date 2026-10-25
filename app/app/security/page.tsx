export const metadata = { title: "Workspace security", robots: { index: false, follow: false } };

export default function WorkspaceSecurityPage() {
  return <>
    <header className="workspace-heading"><p className="eyebrow">Workspace controls</p><h1>Security and AI processing</h1><p>Review what this phase stores and where content is processed.</p></header>
    <section className="security-ledger"><div><span>LLM vendor</span><strong>None in this phase</strong><p>Source and asset text is not sent to an LLM. A local hashed lexical vector supports source passage retrieval; campaign scans are not enabled.</p></div><div><span>Workspace permission</span><strong>Off by default</strong><p>Each organisation has a server-side AI-processing permission. The deployment must also enable an approved provider before any future LLM work can run.</p></div><div><span>Secrets</span><strong>Server-side only</strong><p>API keys and storage credentials are read from environment variables. Session and invite secrets are stored as hashes.</p></div><div><span>Files</span><strong>Private storage provisioned</strong><p>Approved source documents are stored in private local or S3-compatible storage. Access requires organisation membership and a short-lived signed link.</p></div></section>
    <p className="security-disclaimer">These are implementation details for the current local phase. They are not a production security certification.</p>
  </>;
}
