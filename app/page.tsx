import Link from "next/link";
import { LazyCampaignGraph } from "@/app/lazy-graph";
import { TrackedLink } from "@/app/ui";

export default function HomePage() {
  return (
    <>
      <section className="hero wrap">
        <div className="hero-copy">
          <h1>One campaign.<br />One source of truth.</h1>
          <p className="hero-position">Brand governance, made reviewable.</p>
          <p className="hero-lede">BrandLens checks what your campaign says across every channel against the material your team has approved. Every finding shows its evidence. People make the call.</p>
          <div className="actions"><TrackedLink className="button button-primary" href="/demo" label="Explore the guided demo">Explore the guided demo</TrackedLink><Link className="text-link" href="/how-it-works">How it works</Link></div>
          <p className="prototype-note">A source-based reviewer. Not a publishing engine or compliance certification.</p>
        </div>
        <div className="hero-visual" aria-label="Campaign facts connected to approved sources and assets">
          <LazyCampaignGraph />
          <div className="visual-caption"><span>CAMPAIGN VIEW</span><span>Evidence connected, conflicts visible</span></div>
        </div>
      </section>

      <section className="band"><div className="wrap band-inner"><p className="eyebrow">The gap in today’s workflow</p><h2>A campaign can be wrong between the assets.</h2><p>Each post may look fine by itself. But one says 20% off, another says 30%. BrandLens compares the whole campaign and points back to the approved material behind each finding.</p><Link className="text-link" href="/problem">See the problem clearly</Link></div></section>

      <section className="section wrap"><div className="section-heading"><div><p className="eyebrow">Evidence before opinion</p><h2>Review the change.<br />See the source.</h2></div><p>Every finding carries the highlighted line, source or rule, confidence and a suggested edit. The creator can accept, edit or dismiss it with a reason.</p></div><FindingPreview /></section>

      <section className="section section-muted"><div className="wrap"><div className="section-heading"><div><p className="eyebrow">How it works</p><h2>From trusted material<br />to human sign-off.</h2></div><p>Exact rules, evidence-backed checks and campaign comparison work together. A named reviewer keeps the final decision.</p></div><div className="steps-grid">{["Set up approved sources", "Create a campaign", "Scan and resolve findings", "Record reviewer approval"].map((step, index) => <div className="step-card" key={step}><span>0{index + 1}</span><h3>{step}</h3></div>)}</div><Link className="text-link" href="/how-it-works">Walk through the workflow</Link></div></section>

      <section className="closing-cta wrap"><p className="eyebrow">See the review flow</p><h2>Try the skincare<br />campaign simulation.</h2><p>Explore the proposal’s seeded scenario: a claim, a conflicting offer, a logo version and a reviewer decision.</p><TrackedLink className="button button-primary" href="/demo" label="Open the demo">Open the demo</TrackedLink></section>
    </>
  );
}

function FindingPreview() {
  return <div className="finding-preview"><div className="finding-source"><div className="mini-label">APPROVED PRODUCT SHEET · V3</div><p>“The moisturiser <mark>helps to keep the skin hydrated</mark>.”</p><span className="source-tag">Approved passage</span></div><div className="finding-suggested"><div className="mini-label">INSTAGRAM CAPTION · FINDING 01</div><p>“Our moisturiser <del>cures acne in 24 hours</del> <ins>helps keep skin hydrated</ins>.”</p><div className="finding-meta"><span className="severity severity-high">Needs review</span><span>Evidence linked · 92% confidence</span></div></div></div>;
}
