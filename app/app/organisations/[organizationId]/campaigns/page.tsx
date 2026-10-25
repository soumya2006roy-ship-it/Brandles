import { CampaignList } from "@/app/app/organisations/campaigns/campaign-list";

export const metadata = { title: "Campaigns", robots: { index: false, follow: false } };

export default async function CampaignsPage({ params }: { params: Promise<{ organizationId: string }> }) {
  const { organizationId } = await params;
  return <CampaignList organizationId={organizationId}/>;
}
