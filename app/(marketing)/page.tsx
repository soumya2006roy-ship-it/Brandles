import Link from "next/link";
import { LazyCampaignGraph } from "@/app/lazy-graph";
import { TrackedLink } from "@/app/ui";

export default function HomePage() {
  return (
    <main id="main-content">
      <section className="hero wrap">
        <div className="hero-copy">
          <h1>Catch campaign conflicts before approval.</h1>
          <p className="hero-position">Brand governance, made reviewable.</p>
          <p className="hero-lede">Compare campaign assets with approved brand material and with one another. Each finding points to its evidence, and a person decides what changes.</p>
          <div className="actions">
            <TrackedLink className="button button-primary" href="/signup" label="Create your organisation">Create your organisation</TrackedLink>
            <Link className="text-link" href="/login">Log in</Link>
          </div>
          <p className="prototype-note">A source-based reviewer. Not a publishing engine or compliance certification.</p>
        </div>
        <div className="hero-visual" aria-label="Campaign facts connected to approved sources and assets">
          <LazyCampaignGraph />
          <div className="visual-caption"><span>CAMPAIGN VIEW</span><span>Evidence connected, conflicts visible</span></div>
        </div>
      </section>

      <section className="band"><div className="wrap band-inner"><p className="eyebrow">The gap in today’s workflow</p><h2>A campaign can be wrong between the assets.</h2><p>BrandLens compares approved sources with campaign assets and checks how the assets agree with one another. Reviewers can trace each finding to evidence before deciding what to do.</p><Link className="text-link" href="/problem">See the problem clearly</Link></div></section>

      <section className="section section-muted"><div className="wrap"><div className="section-heading"><div><p className="eyebrow">A shared review workflow</p><h2>From trusted sources<br />to a recorded decision.</h2></div><p>Organisation members use role-based access to maintain evidence, prepare campaigns and review findings.</p></div><div className="steps-grid">{["Set up approved sources", "Create a campaign and add assets", "Scan and resolve findings", "Submit for reviewer approval"].map((step, index) => <div className="step-card" key={step}><span>0{index + 1}</span><h3>{step}</h3></div>)}</div><Link className="text-link" href="/how-it-works">Read how the workflow works</Link></div></section>

      <section className="section wrap"><div className="section-heading"><div><p className="eyebrow">Evidence before opinion</p><h2>Inspect the source.<br />Make the decision.</h2></div><p>Findings link to approved passages and campaign facts. A reviewer makes the decision, and the selected asset version is recorded.</p></div><div className="actions"><Link className="button button-primary" href="/signup">Create your organisation</Link><Link className="text-link" href="/join">Join with an invite code</Link></div></section>

      <section className="closing-cta wrap"><p className="eyebrow">Questions about access?</p><h2>Start with your organisation.</h2><p>Create an organisation, log in to an existing account, or contact the BrandLens team.</p><div className="actions"><TrackedLink className="button button-primary" href="/signup" label="Create your organisation">Create your organisation</TrackedLink><Link className="text-link" href="/contact">Contact us</Link></div></section>
    </main>
  );
}
