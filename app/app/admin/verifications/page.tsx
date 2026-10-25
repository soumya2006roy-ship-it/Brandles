import { VerificationQueue } from "@/app/app/admin/verifications/verification-queue";

export const metadata = { title: "Organisation verification queue", robots: { index: false, follow: false } };
export default function VerificationPage() { return <VerificationQueue/>; }
