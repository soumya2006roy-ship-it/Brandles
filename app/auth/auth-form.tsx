"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { apiRequest } from "@/app/lib/api-client";

type Mode = "login" | "register" | "forgot" | "reset";

export function AuthForm({ mode }: { mode: Mode }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);
  const [resetToken, setResetToken] = useState("");

  useEffect(() => {
    if (mode === "reset") {
      const timer = window.setTimeout(() => {
        const url = new URL(window.location.href);
        setResetToken(url.searchParams.get("token") ?? "");
        if (url.searchParams.has("token")) window.history.replaceState(null, "", "/reset-password");
      }, 0);
      return () => window.clearTimeout(timer);
    }
  }, [mode]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    setPending(true);
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "");
    try {
      if (mode === "register") {
        await apiRequest("auth/register", { method: "POST", body: JSON.stringify({ email, display_name: form.get("display_name"), password: form.get("password") }) });
        await apiRequest("auth/login", { method: "POST", body: JSON.stringify({ email, password: form.get("password") }) });
        router.replace("/app");
        router.refresh();
      } else if (mode === "login") {
        await apiRequest("auth/login", { method: "POST", body: JSON.stringify({ email, password: form.get("password") }) });
        router.replace("/app");
        router.refresh();
      } else if (mode === "forgot") {
        const result = await apiRequest<{ message: string }>("auth/password-reset", { method: "POST", body: JSON.stringify({ email }) });
        setMessage(result.message);
      } else {
        const token = resetToken || String(form.get("token") ?? "");
        await apiRequest("auth/password-reset/confirm", { method: "POST", body: JSON.stringify({ token, password: form.get("password") }) });
        setMessage("Password updated. Sign in with your new password.");
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Something went wrong. Please try again.");
    } finally {
      setPending(false);
    }
  }

  const titles: Record<Mode, string> = {
    login: "Sign in to your workspace",
    register: "Create your BrandLens account",
    forgot: "Reset your password",
    reset: "Choose a new password",
  };
  const descriptions: Record<Mode, string> = {
    login: "Use your email address to continue.",
    register: "Create an account and continue straight to your workspace.",
    forgot: "If an account matches, we will send a single-use reset link.",
    reset: "Choose a password with at least 12 characters.",
  };

  return <main className="auth-page"><div className="auth-panel"><p className="eyebrow">BrandLens workspace</p><h1>{titles[mode]}</h1><p className="auth-description">{descriptions[mode]}</p>
    <form className="auth-form" onSubmit={submit}>
      {mode === "register" && <label className="form-field">Your name<input name="display_name" autoComplete="name" required minLength={2} maxLength={120}/></label>}
      {(mode === "login" || mode === "register" || mode === "forgot") && <label className="form-field">Work email<input name="email" type="email" autoComplete="email" required maxLength={320}/></label>}
      {mode === "reset" && !resetToken && <label className="form-field">Reset token<input name="token" autoComplete="off" required minLength={20}/></label>}
      {(mode === "login" || mode === "register" || mode === "reset") && <label className="form-field">{mode === "reset" ? "New password" : "Password"}<input name="password" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} required minLength={mode === "login" ? 1 : 12} maxLength={128}/></label>}
      {error && <p className="auth-message auth-error" role="alert">{error}</p>}
      {message && <p className="auth-message auth-success" role="status">{message}</p>}
      <button className="button button-primary" type="submit" disabled={pending}>{pending ? "Please wait…" : mode === "login" ? "Sign in" : mode === "register" ? "Create account" : mode === "forgot" ? "Send reset link" : "Update password"}</button>
    </form>
    <nav className="auth-links" aria-label="Account links">
      {mode === "login" && <><Link href="/sign-up">Create an account</Link><Link href="/forgot-password">Forgot password?</Link></>}
      {mode === "register" && <Link href="/login">Already have an account? Sign in</Link>}
      {mode === "forgot" && <Link href="/login">Return to sign in</Link>}
      {mode === "reset" && <Link href="/login">Return to sign in</Link>}
      <Link href="/">BrandLens public site</Link>
    </nav>
  </div></main>;
}
