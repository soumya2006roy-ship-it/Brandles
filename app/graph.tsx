"use client";

export function CampaignGraph() {
  return (
    <div className="graph-card">
      <div className="graph-top">
        <span className="graph-kicker">EVIDENCE MAP · OFFER CHECK</span>
        <span className="graph-live">Conflict found</span>
      </div>
      <svg className="graph-svg" viewBox="0 0 560 330" role="img" aria-labelledby="graph-title graph-description">
        <title id="graph-title">Campaign Consistency Graph</title>
        <desc id="graph-description">Three campaign assets connect to an approved offer. One email discount conflicts with the approved 20 percent offer.</desc>
        <path className="graph-line graph-line-approved" d="M96 76 C180 76 182 165 260 165" />
        <path className="graph-line graph-line-conflict" d="M464 76 C380 76 378 165 300 165" />
        <path className="graph-line graph-line-approved" d="M96 252 C180 252 182 165 260 165" />
        <path className="graph-line" d="M300 165 C370 165 376 252 464 252" />
        <g className="graph-node node-source"><rect x="18" y="42" width="158" height="68" rx="2" /><text x="34" y="69">APPROVED SOURCE</text><text x="34" y="91" className="node-value">Offer · 20% off</text></g>
        <g className="graph-node node-asset"><rect x="384" y="42" width="158" height="68" rx="2" /><text x="400" y="69">EMAIL</text><text x="400" y="91" className="node-value">Offer · 30% off</text></g>
        <g className="graph-node node-asset"><rect x="18" y="218" width="158" height="68" rx="2" /><text x="34" y="245">INSTAGRAM</text><text x="34" y="267" className="node-value">Claim · Hydration</text></g>
        <g className="graph-node node-asset"><rect x="384" y="218" width="158" height="68" rx="2" /><text x="400" y="245">POSTER</text><text x="400" y="267" className="node-value">Logo · Previous</text></g>
        <g className="graph-center"><circle cx="280" cy="165" r="42" /><circle className="orbit" cx="280" cy="165" r="53" /><text x="280" y="161" textAnchor="middle">CAMPAIGN</text><text x="280" y="178" textAnchor="middle" className="center-sub">3 assets</text></g>
        <circle className="conflict-pulse" cx="398" cy="102" r="6" />
      </svg>
      <div className="graph-legend"><span>Approved source</span><span>Conflict</span><span>Campaign asset</span></div>
    </div>
  );
}
