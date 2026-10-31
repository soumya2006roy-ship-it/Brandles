import { BrandHealthDashboard } from "@/app/app/organisations/brand-health/brand-health-dashboard";

export const metadata = { title: "Brand Health", robots: { index: false, follow: false } };

export default async function BrandHealthPage({ params }: { params: Promise<{ organizationId: string }> }) {
  const { organizationId } = await params;
  return <BrandHealthDashboard organizationId={organizationId}/>;
}
