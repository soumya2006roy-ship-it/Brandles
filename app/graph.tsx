"use client";

export function CampaignGraph() {
  return (
    <div className="graph-card">
      <div className="graph-top">
        <span className="graph-kicker">CAMPAIGN CONSISTENCY GRAPH</span>
        <span className="graph-live">Evidence linked</span>
      </div>
      <svg className="graph-svg" viewBox="0 0 560 330" role="img" aria-labelledby="graph-title graph-description">
        <title id="graph-title">Campaign Consistency Graph</title>
        <desc id="graph-description">Approved source material connects to campaign assets through their related evidence.</desc>
        <path className="graph-line graph-line-approved" d="M96 76 C180 76 182 165 260 165" />
        <path className="graph-line graph-line-conflict" d="M464 76 C380 76 378 165 300 165" />
        <path className="graph-line graph-line-approved" d="M96 252 C180 252 182 165 260 165" />
        <path className="graph-line" d="M300 165 C370 165 376 252 464 252" />
        <g className="graph-node node-source"><rect x="18" y="42" width="158" height="68" rx="2" /><text x="34" y="69">APPROVED SOURCE</text><text x="34" y="91" className="node-value">Brand guidance</text></g>
        <g className="graph-node node-asset"><rect x="384" y="42" width="158" height="68" rx="2" /><text x="400" y="69">CAMPAIGN ASSET</text><text x="400" y="91" className="node-value">Asset facts</text></g>
        <g className="graph-node node-asset"><rect x="18" y="218" width="158" height="68" rx="2" /><text x="34" y="245">CAMPAIGN ASSET</text><text x="34" y="267" className="node-value">Text and claims</text></g>
        <g className="graph-node node-asset"><rect x="384" y="218" width="158" height="68" rx="2" /><text x="400" y="245">CAMPAIGN ASSET</text><text x="400" y="267" className="node-value">Offer and terms</text></g>
        <g className="graph-center"><circle cx="280" cy="165" r="42" /><circle className="orbit" cx="280" cy="165" r="53" /><text x="280" y="161" textAnchor="middle">CAMPAIGN</text><text x="280" y="178" textAnchor="middle" className="center-sub">connected</text></g>
        <circle className="conflict-pulse" cx="398" cy="102" r="6" />
      </svg>
      <div className="graph-legend"><span>Approved source</span><span>Evidence link</span><span>Campaign asset</span></div>
    </div>
  );
}
