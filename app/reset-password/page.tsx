import { AuthForm } from "@/app/auth/auth-form";

export const metadata = { title: "Choose a new password", robots: { index: false, follow: false } };
export default function ResetPasswordPage() { return <AuthForm mode="reset"/>; }
