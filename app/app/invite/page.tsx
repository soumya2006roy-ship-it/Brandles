"use client";

import { FormEvent, useState } from "react";
import { apiRequest } from "@/app/lib/api-client";

export default function RedeemInvitePage() {
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(""); setMessage("");
    const form = new FormData(event.currentTarget);
    try {
      const result = await apiRequest<{ message: string }>("invites/redeem", { method: "POST", body: JSON.stringify({ code: form.get("code") }) });
      setMessage(result.message);
      event.currentTarget.reset();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not redeem this invite."); }
  }
  return <><header className="workspace-heading narrow"><p className="eyebrow">Join an organisation</p><h1>Redeem an invite</h1><p>Enter the code shared by an organisation administrator. Invite codes are not sent in URLs.</p></header><form className="workspace-form" onSubmit={submit}><label className="form-field">Invite code<input name="code" autoComplete="off" required minLength={20} maxLength={200}/></label>{error && <p className="auth-message auth-error" role="alert">{error}</p>}{message && <p className="auth-message auth-success" role="status">{message}</p>}<button className="button button-primary" type="submit">Join organisation</button></form></>;
}
