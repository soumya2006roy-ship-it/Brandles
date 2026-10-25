import { SourceLibrary } from "@/app/app/organisations/sources/source-library";

export const metadata = { title: "Approved sources", robots: { index: false, follow: false } };

export default async function SourcesPage({ params }: { params: Promise<{ organizationId: string }> }) {
  const { organizationId } = await params;
  return <SourceLibrary organizationId={organizationId}/>;
}
