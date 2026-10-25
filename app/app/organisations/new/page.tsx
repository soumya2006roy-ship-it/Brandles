import { OrganisationForm } from "@/app/app/organisations/organisation-form";

export const metadata = { title: "Create organisation", robots: { index: false, follow: false } };
export default function NewOrganisationPage() { return <OrganisationForm/>; }
