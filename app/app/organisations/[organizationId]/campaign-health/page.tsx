import { CampaignHealth } from "@/app/app/organisations/campaign-health/campaign-health";

export const metadata = { title: "Campaign health", robots: { index: false, follow: false } };

export default async function CampaignHealthPage({ params }: { params: Promise<{ organizationId: string }> }) {
  const { organizationId } = await params;
  return <CampaignHealth organizationId={organizationId}/>;
}
