"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useRef, useState } from "react";
import { ApiError, apiRequest } from "@/app/lib/api-client";
import { LanguageSelect, useLocale } from "@/app/i18n";

type Mode = "login" | "register" | "forgot-question" | "reset";

const recoveryQuestions = [
  ["first_school", "auth.recoveryFirstSchool"],
  ["birth_city", "auth.recoveryBirthCity"],
  ["first_pet", "auth.recoveryFirstPet"],
] as const;

const transientLoginRetryDelays = [500, 1_000, 2_000, 4_000, 8_000, 16_000, 20_000];

async function loginWithRetry(email: string, password: string) {
  for (let attempt = 0; ; attempt += 1) {
    try {
      return await apiRequest("auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
    } catch (cause) {
      const retryable = cause instanceof TypeError || (cause instanceof ApiError && [502, 503, 504].includes(cause.status));
      const delay = transientLoginRetryDelays[attempt];
      if (!retryable || delay === undefined) throw cause;
      await new Promise<void>((resolve) => window.setTimeout(resolve, delay));
    }
  }
}

export function AuthForm({ mode, initialResetToken = "" }: { mode: Mode; initialResetToken?: string }) {
  const router = useRouter();
  const { t } = useLocale();
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);
  const [resetToken] = useState(initialResetToken);

  useEffect(() => {
    if (mode === "reset") {
      const timer = window.setTimeout(() => {
        const url = new URL(window.location.href);
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
        await loginWithRetry(email, String(form.get("password") ?? ""));
        window.location.replace("/app");
      } else if (mode === "login") {
        await loginWithRetry(email, String(form.get("password") ?? ""));
        window.location.replace("/app");
      } else if (mode === "forgot-question") {
        const result = await apiRequest<{ reset_token: string | null }>("auth/password-reset/recovery-question", { method: "POST", body: JSON.stringify({ email, recovery_question: form.get("recovery_question"), recovery_answer: form.get("recovery_answer") }) });
        if (!result.reset_token) setError(t("auth.recoveryMismatch"));
        else router.replace(`/reset-password?token=${encodeURIComponent(result.reset_token)}`);
      } else {
        const password = String(form.get("password") ?? "");
        if (password !== form.get("confirm_password")) {
          setError(t("auth.passwordMismatch"));
          return;
        }
        await apiRequest("auth/password-reset/confirm", { method: "POST", body: JSON.stringify({ token: resetToken, password }) });
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
    "forgot-question": t("auth.recoveryTitle"),
    reset: t("auth.resetTitle"),
  };
  const descriptions: Record<Mode, string> = {
    login: t("auth.loginDescription"),
    register: t("auth.registerDescription"),
    "forgot-question": t("auth.recoveryDescription"),
    reset: t("auth.resetDescription"),
  };

  return <main className="auth-page"><div className="auth-panel"><div className="auth-locale-row"><p className="eyebrow">{t("auth.workspace")}</p><LanguageSelect/></div><h1>{titles[mode]}</h1><p className="auth-description">{descriptions[mode]}</p>
    <form className="auth-form" onSubmit={submit}>
      {mode === "register" && <label className="form-field">{t("auth.name")}<input name="display_name" autoComplete="name" required minLength={2} maxLength={120}/></label>}
      {(mode === "login" || mode === "register") && <label className="form-field">{t("auth.email")}<input name="email" type="email" autoComplete="email" required maxLength={320}/></label>}
      {mode === "register" && <label className="form-field">{t("auth.recoveryQuestion")}<select name="recovery_question" required defaultValue=""><option value="" disabled>{t("auth.chooseRecoveryQuestion")}</option>{recoveryQuestions.map(([value, label]) => <option value={value} key={value}>{t(label)}</option>)}</select></label>}
      {mode === "register" && <><label className="form-field">{t("auth.recoveryAnswer")}<input name="recovery_answer" autoComplete="off" required minLength={2} maxLength={200}/></label><p className="field-help">{t("auth.recoveryHint")}</p></>}
      {mode === "forgot-question" && <>
        <label className="form-field">{t("auth.email")}<input name="email" type="email" autoComplete="email" required maxLength={320}/></label>
        <label className="form-field">{t("auth.recoveryQuestion")}<select name="recovery_question" required defaultValue=""><option value="" disabled>{t("auth.chooseRecoveryQuestion")}</option>{recoveryQuestions.map(([value, label]) => <option value={value} key={value}>{t(label)}</option>)}</select></label>
        <label className="form-field">{t("auth.recoveryAnswer")}<input name="recovery_answer" autoComplete="off" required minLength={2} maxLength={200}/></label>
        <p className="field-help">{t("auth.recoveryHint")}</p>
      </>}
      {(mode === "login" || mode === "register" || mode === "reset") && <PasswordField label={mode === "reset" ? t("auth.newPassword") : t("auth.password")} autoComplete={mode === "login" ? "current-password" : "new-password"} minLength={mode === "login" ? 1 : 12} t={t}/>}
      {mode === "reset" && <PasswordField name="confirm_password" id="auth-confirm-password" label={t("auth.confirmPassword")} t={t}/>}
      {mode === "login" && <p className="auth-message auth-note" role="note">{t("auth.adminHint")}</p>}
      {error && <p className="auth-message auth-error" role="alert">{error}</p>}
      {message && <p className="auth-message auth-success" role="status">{message}</p>}
      <button className="button button-primary" type="submit" disabled={pending}>{pending ? t("auth.wait") : mode === "login" ? t("auth.signIn") : mode === "register" ? t("auth.submitRegister") : mode === "forgot-question" ? t("auth.recoveryVerify") : t("auth.updatePassword")}</button>
    </form>
    <nav className="auth-links" aria-label={t("auth.accountLinks")}>
      {mode === "login" && <><Link href="/sign-up">{t("auth.createAccount")}</Link><Link href="/forgot-password">{t("auth.forgot")}</Link></>}
      {mode === "register" && <Link href="/login">{t("auth.existingAccount")}</Link>}
      {mode === "forgot-question" && <Link href="/login">{t("auth.returnSignIn")}</Link>}
      {mode === "reset" && <Link href="/login">{t("auth.returnSignIn")}</Link>}
      <Link href="/">{t("auth.publicSite")}</Link>
    </nav>
  </div></main>;
}

function PasswordField({ label, name = "password", id = "auth-password", autoComplete = "new-password", minLength = 12, t }: {
  label: string;
  name?: string;
  id?: string;
  autoComplete?: string;
  minLength?: number;
  t: (key: string) => string;
}) {
  const [showPassword, setShowPassword] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const selection = useRef<{ start: number; end: number; direction: "forward" | "backward" | "none" | null } | null>(null);

  function toggleVisibility() {
    const input = inputRef.current;
    if (input) selection.current = { start: input.selectionStart ?? 0, end: input.selectionEnd ?? 0, direction: input.selectionDirection };
    setShowPassword((value) => !value);
    if (!input || !selection.current) return;
    input.focus({ preventScroll: true });
    input.setSelectionRange(selection.current.start, selection.current.end, selection.current.direction ?? undefined);
  }

  return <div className="form-field"><label htmlFor={id}>{label}</label><div className="password-field-control"><input ref={inputRef} id={id} name={name} type={showPassword ? "text" : "password"} autoComplete={autoComplete} required minLength={minLength} maxLength={128}/><button className="password-visibility-toggle" type="button" aria-label={t(showPassword ? "auth.hidePassword" : "auth.showPassword")} aria-controls={id} aria-pressed={showPassword} onPointerDown={(event) => event.preventDefault()} onMouseDown={(event) => event.preventDefault()} onClick={toggleVisibility}>{t(showPassword ? "auth.hidePassword" : "auth.showPassword")}</button></div></div>;
}
