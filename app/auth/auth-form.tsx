"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { apiRequest } from "@/app/lib/api-client";
import { LanguageSelect, useLocale } from "@/app/i18n";

type Mode = "login" | "register" | "forgot" | "forgot-question" | "reset";

const recoveryQuestions = [
  ["first_school", "auth.recoveryFirstSchool"],
  ["birth_city", "auth.recoveryBirthCity"],
  ["first_pet", "auth.recoveryFirstPet"],
] as const;

export function AuthForm({ mode }: { mode: Mode }) {
  const { t } = useLocale();
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
        await apiRequest("auth/register", { method: "POST", body: JSON.stringify({ email, display_name: form.get("display_name"), password: form.get("password"), recovery_question: form.get("recovery_question"), recovery_answer: form.get("recovery_answer") }) });
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
      } else if (mode === "forgot-question") {
        const result = await apiRequest<{ message: string }>("auth/password-reset/recovery-question", { method: "POST", body: JSON.stringify({ email, recovery_question: form.get("recovery_question"), recovery_answer: form.get("recovery_answer"), password: form.get("password") }) });
        setMessage(result.message);
      } else {
        const token = resetToken || String(form.get("token") ?? "");
        await apiRequest("auth/password-reset/confirm", { method: "POST", body: JSON.stringify({ token, password: form.get("password") }) });
        setMessage(t("auth.resetSuccess"));
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : t("auth.genericError"));
    } finally {
      setPending(false);
    }
  }

  const titles: Record<Mode, string> = {
    login: t("auth.loginTitle"),
    register: t("auth.registerTitle"),
    forgot: t("auth.forgotTitle"),
    "forgot-question": t("auth.recoveryTitle"),
    reset: t("auth.resetTitle"),
  };
  const descriptions: Record<Mode, string> = {
    login: t("auth.loginDescription"),
    register: t("auth.registerDescription"),
    forgot: t("auth.forgotDescription"),
    "forgot-question": t("auth.recoveryDescription"),
    reset: t("auth.resetDescription"),
  };

  return <main className="auth-page"><div className="auth-panel"><div className="auth-locale-row"><p className="eyebrow">{t("auth.workspace")}</p><LanguageSelect/></div><h1>{titles[mode]}</h1><p className="auth-description">{descriptions[mode]}</p>
    <form className="auth-form" onSubmit={submit}>
      {mode === "register" && <label className="form-field">{t("auth.name")}<input name="display_name" autoComplete="name" required minLength={2} maxLength={120}/></label>}
      {(mode === "login" || mode === "register" || mode === "forgot") && <label className="form-field">{t("auth.email")}<input name="email" type="email" autoComplete="email" required maxLength={320}/></label>}
      {mode === "register" && <label className="form-field">{t("auth.recoveryQuestion")}<select name="recovery_question" required defaultValue=""><option value="" disabled>{t("auth.chooseRecoveryQuestion")}</option>{recoveryQuestions.map(([value, label]) => <option value={value} key={value}>{t(label)}</option>)}</select></label>}
      {mode === "register" && <><label className="form-field">{t("auth.recoveryAnswer")}<input name="recovery_answer" autoComplete="off" required minLength={2} maxLength={200}/></label><p className="field-help">{t("auth.recoveryHint")}</p></>}
      {mode === "forgot-question" && <>
        <label className="form-field">{t("auth.email")}<input name="email" type="email" autoComplete="email" required maxLength={320}/></label>
        <label className="form-field">{t("auth.recoveryQuestion")}<select name="recovery_question" required defaultValue=""><option value="" disabled>{t("auth.chooseRecoveryQuestion")}</option>{recoveryQuestions.map(([value, label]) => <option value={value} key={value}>{t(label)}</option>)}</select></label>
        <label className="form-field">{t("auth.recoveryAnswer")}<input name="recovery_answer" autoComplete="off" required minLength={2} maxLength={200}/></label>
        <label className="form-field">{t("auth.newPassword")}<input name="password" type="password" autoComplete="new-password" required minLength={12} maxLength={128}/></label>
        <p className="field-help">{t("auth.recoveryHint")}</p>
      </>}
      {mode === "reset" && !resetToken && <label className="form-field">{t("auth.resetToken")}<input name="token" autoComplete="off" required minLength={20}/></label>}
      {(mode === "login" || mode === "register" || mode === "reset") && <label className="form-field">{mode === "reset" ? t("auth.newPassword") : t("auth.password")}<input name="password" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} required minLength={mode === "login" ? 1 : 12} maxLength={128}/></label>}
      {mode === "login" && <p className="auth-message auth-note" role="note">{t("auth.adminHint")}</p>}
      {error && <p className="auth-message auth-error" role="alert">{error}</p>}
      {message && <p className="auth-message auth-success" role="status">{message}</p>}
      <button className="button button-primary" type="submit" disabled={pending}>{pending ? t("auth.wait") : mode === "login" ? t("auth.signIn") : mode === "register" ? t("auth.submitRegister") : mode === "forgot" ? t("auth.sendReset") : t("auth.updatePassword")}</button>
    </form>
    <nav className="auth-links" aria-label={t("auth.accountLinks")}>
      {mode === "login" && <><Link href="/sign-up">{t("auth.createAccount")}</Link><Link href="/forgot-password">{t("auth.forgot")}</Link></>}
      {mode === "register" && <Link href="/login">{t("auth.existingAccount")}</Link>}
      {mode === "forgot" && <Link href="/login">{t("auth.returnSignIn")}</Link>}
      {mode === "forgot" && <Link href="/reset-with-question">{t("auth.recoveryLink")}</Link>}
      {mode === "forgot-question" && <Link href="/forgot-password">{t("auth.emailResetLink")}</Link>}
      {mode === "forgot-question" && <Link href="/login">{t("auth.returnSignIn")}</Link>}
      {mode === "reset" && <Link href="/login">{t("auth.returnSignIn")}</Link>}
      <Link href="/">{t("auth.publicSite")}</Link>
    </nav>
  </div></main>;
}
