import { AuthForm } from "@/app/auth/auth-form";
import { redirect } from "next/navigation";

export const metadata = { title: "Choose a new password", robots: { index: false, follow: false } };
export default async function ResetPasswordPage({ searchParams }: { searchParams: Promise<{ token?: string | string[] }> }) {
  const tokenParam = (await searchParams).token;
  const token = Array.isArray(tokenParam) ? tokenParam[0] : tokenParam;
  const backend = process.env.BRANDLENS_BACKEND_URL;
  if (!token || !backend) redirect("/forgot-password");

  let valid = false;
  try {
    const response = await fetch(new URL(`/api/v1/auth/password-reset/confirm/validate?token=${encodeURIComponent(token)}`, backend), { cache: "no-store" });
    const result = response.ok ? await response.json() as { valid?: boolean } : null;
    valid = Boolean(result?.valid);
  } catch { /* The reset flow is unavailable, so do not render an unverified form. */ }
  if (!valid) redirect("/forgot-password");

  return <AuthForm mode="reset" initialResetToken={token}/>;
}
