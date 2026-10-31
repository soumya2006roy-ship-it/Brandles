import { AuthForm } from "@/app/auth/auth-form";

export const metadata = { title: "Recover account", robots: { index: false, follow: false } };

export default function RecoveryQuestionPage() { return <AuthForm mode="forgot-question"/>; }
