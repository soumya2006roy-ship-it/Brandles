"use client";

export function CampaignGraph() {
  return (
    <figure className="graph-card" aria-labelledby="campaign-graph-title" aria-describedby="campaign-graph-description">
      <figcaption className="graph-top">
        <span id="campaign-graph-title" className="graph-kicker">CAMPAIGN CONSISTENCY GRAPH</span>
        <span className="graph-example-label">Illustrative scenario</span>
      </figcaption>
      <p id="campaign-graph-description" className="graph-description">An approved skincare offer is compared with an Instagram post, an email and a poster. The review highlights an unsupported claim, a discount mismatch and an old logo.</p>
      <div className="graph-example">
        <article className="graph-source-card">
          <span className="graph-card-index">APPROVED SOURCE</span>
          <h3>Product sheet</h3>
          <p>“Helps to keep the skin hydrated.”</p>
          <div className="graph-offer"><span>Approved offer</span><strong>20% off</strong><small>Until 30 November</small></div>
        </article>
        <div className="graph-connections" aria-hidden="true"><span/><span/><span/></div>
        <article className="graph-asset-card graph-asset-claim">
          <div><span className="graph-card-index">INSTAGRAM</span><span className="graph-asset-status">Claim to review</span></div>
          <p>“Cures acne in 24 hours.”</p>
          <small>Unsupported claim</small>
        </article>
        <article className="graph-asset-card graph-asset-offer">
          <div><span className="graph-card-index">EMAIL</span><span className="graph-asset-status">Offer mismatch</span></div>
          <p><strong>30% off</strong> in the email vs 20% in the approved source</p>
          <small>Conflicting discount</small>
        </article>
        <article className="graph-asset-card graph-asset-logo">
          <div><span className="graph-card-index">POSTER</span><span className="graph-asset-status">Asset to replace</span></div>
          <p>Artwork contains an older logo.</p>
          <small>Wrong logo version</small>
        </article>
      </div>
      <div className="graph-outcome"><span className="graph-outcome-mark" aria-hidden="true">!</span><p><strong>One campaign, three channels.</strong> Each finding stays connected to the approved material a person can review.</p></div>
    </figure>
  );
}
