import { RulesEditor } from "@/app/app/organisations/rules/rules-editor";

export const metadata = { title: "Structured rules", robots: { index: false, follow: false } };

export default async function RulesPage({ params }: { params: Promise<{ organizationId: string }> }) {
  const { organizationId } = await params;
  return <RulesEditor organizationId={organizationId}/>;
}
