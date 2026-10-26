import { AuditLog } from "@/app/app/organisations/audit-log";

export default async function AuditPage({ params }: { params: Promise<{ organizationId: string }> }) {
  const { organizationId } = await params;
  return <AuditLog organizationId={organizationId}/>;
}
