"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { apiRequest } from "@/app/lib/api-client";

export function OrganisationForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setPending(true);
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try {
      await apiRequest("orgs", { method: "POST", body: JSON.stringify(values) });
      router.replace("/app");
      router.refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not submit this organisation.");
    } finally { setPending(false); }
  }
  return <>
    <header className="workspace-heading narrow"><p className="eyebrow">New workspace</p><h1>Organisation details</h1><p>Submissions enter the verification queue. Workspace invites and material remain unavailable until approval.</p></header>
    <form className="workspace-form" onSubmit={submit}>
      <label className="form-field">Organisation name<input name="name" required minLength={2} maxLength={180}/></label>
      <label className="form-field">Industry<input name="industry" required minLength={2} maxLength={120}/></label>
      <label className="form-field">Official organisation email<input name="official_email" type="email" required maxLength={320}/></label>
      <label className="form-field">Organisation website<input name="website" type="url" placeholder="https://example.com" required maxLength={500}/></label>
      <label className="form-field">Contact person<input name="contact_person" autoComplete="name" required minLength={2} maxLength={120}/></label>
      {error && <p className="auth-message auth-error" role="alert">{error}</p>}
      <div className="form-actions"><button className="button button-primary" type="submit" disabled={pending}>{pending ? "Submitting…" : "Submit for verification"}</button><button className="button secondary-button" type="button" onClick={() => router.back()}>Cancel</button></div>
    </form>
  </>;
}
