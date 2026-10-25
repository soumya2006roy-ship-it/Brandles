import { AuthForm } from "@/app/auth/auth-form";

export const metadata = { title: "Create account", robots: { index: false, follow: false } };
export default function SignUpPage() { return <AuthForm mode="register"/>; }
