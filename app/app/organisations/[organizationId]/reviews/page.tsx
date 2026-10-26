import { ReviewQueue } from "@/app/app/organisations/reviews/review-queue";

export const metadata = { title: "Reviewer queue", robots: { index: false, follow: false } };

export default async function OrganisationReviewsPage({ params }: { params: Promise<{ organizationId: string }> }) {
  const { organizationId } = await params;
  return <ReviewQueue organizationId={organizationId}/>;
}
