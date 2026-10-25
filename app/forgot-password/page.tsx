import { AuthForm } from "@/app/auth/auth-form";

export const metadata = { title: "Reset password", robots: { index: false, follow: false } };
export default function ForgotPasswordPage() { return <AuthForm mode="forgot"/>; }
