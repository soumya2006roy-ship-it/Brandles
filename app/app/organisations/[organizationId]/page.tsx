import { OrganisationWorkspace } from "@/app/app/organisations/organisation-workspace";

export const metadata = { title: "Organisation workspace", robots: { index: false, follow: false } };
export default async function OrganisationPage({ params }: { params: Promise<{ organizationId: string }> }) {
  const { organizationId } = await params;
  return <OrganisationWorkspace organizationId={organizationId}/>;
}
