import { RulesEditor } from "@/app/app/organisations/rules/rules-editor";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export const metadata = { title: "Structured rules", robots: { index: false, follow: false } };

export default async function RulesPage({ params }: { params: Promise<{ organizationId: string }> }) {
  const { organizationId } = await params;
  const backend = process.env.BRANDLENS_BACKEND_URL;
  const cookieName = process.env.SESSION_COOKIE_NAME ?? "brandlens_session";
  const session = (await cookies()).get(cookieName)?.value;
  if (!backend || !session) redirect("/login");

  let response: Response;
  try {
    response = await fetch(new URL("/api/v1/orgs", backend), {
      headers: { cookie: `${cookieName}=${encodeURIComponent(session)}` },
      cache: "no-store",
    });
  } catch {
    return <main className="page-shell"><p role="alert">The BrandLens API is unavailable. Try again when the service is ready.</p></main>;
  }
  if (response.status === 401) redirect("/login");
  if (!response.ok) return <main className="page-shell"><p role="alert">The organisation role could not be verified. Try again shortly.</p></main>;

  const organizations = await response.json() as { id: string; role: string }[];
  const organization = organizations.find((item) => item.id === organizationId);
  if (!organization) redirect("/app");
  if (organization.role !== "admin" && organization.role !== "creator") redirect(`/app/organisations/${organizationId}`);

  return <RulesEditor organizationId={organizationId}/>;
}
