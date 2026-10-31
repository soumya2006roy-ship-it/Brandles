import { VisualCompliance } from "@/app/app/organisations/visual-compliance/visual-compliance";

export const metadata = { title: "Visual compliance", robots: { index: false, follow: false } };

export default async function VisualCompliancePage({ params }: { params: Promise<{ organizationId: string }> }) {
  const { organizationId } = await params;
  return <VisualCompliance organizationId={organizationId}/>;
}
