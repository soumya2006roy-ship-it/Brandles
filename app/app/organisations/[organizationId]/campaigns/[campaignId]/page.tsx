import { CampaignWorkspace } from "@/app/app/organisations/campaigns/campaign-workspace";

export const metadata = { title: "Campaign assets", robots: { index: false, follow: false } };

export default async function CampaignAssetsPage({ params }: { params: Promise<{ organizationId: string; campaignId: string }> }) {
  const { organizationId, campaignId } = await params;
  return <CampaignWorkspace organizationId={organizationId} campaignId={campaignId}/>;
}
