"use client";

import dynamic from "next/dynamic";

const CampaignGraph = dynamic(() => import("@/app/graph").then((module) => module.CampaignGraph), {
  loading: () => <div className="graph-loading skeleton" aria-label="Loading campaign consistency graph" />,
});

export function LazyCampaignGraph() {
  return <CampaignGraph />;
}
