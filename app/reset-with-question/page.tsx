import { redirect } from "next/navigation";

export const metadata = { title: "Recover account", robots: { index: false, follow: false } };

export default function RecoveryQuestionPage() { redirect("/forgot-password"); }
