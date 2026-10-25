"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { track } from "@/app/track";
import { useToast } from "@/app/ui";

type FieldName = "name" | "email" | "organization" | "message";
type FieldErrors = Partial<Record<FieldName, string>>;

export function ContactForm() {
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState("");
  const [success, setSuccess] = useState("");
  const [pending, setPending] = useState(false);
  const notify = useToast();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    setPending(true);
    setErrors({});
    setFormError("");
    setSuccess("");
    const formData = new FormData(event.currentTarget);
    const payload = Object.fromEntries(formData.entries());
    try {
      const response = await fetch("/api/contact", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      const result = await response.json() as { message?: string; fields?: FieldErrors };
      if (!response.ok) {
        setErrors(result.fields ?? {});
        setFormError(result.message ?? "We couldn’t send your message. Please try again.");
        track("contact_submit_error", { source: "contact-form", reason: response.status === 400 ? "validation" : "delivery" });
        notify(result.message ?? "We couldn’t send your message.", "error");
        return;
      }
      setSuccess(result.message ?? "Thanks , your message has been received.");
      form.reset();
      track("contact_submit_success", { source: "contact-form" });
      notify("Your message was sent.", "success");
    } catch {
      setFormError("We couldn’t connect just now. Check your connection and try again.");
      track("contact_submit_error", { source: "contact-form", reason: "network" });
      notify("We couldn’t connect to send your message.", "error");
    } finally {
      setPending(false);
    }
  }

  return <form className="contact-form" onSubmit={submit} noValidate>
    {formError && <div className="form-error-summary" role="alert" tabIndex={-1}>{formError}</div>}
    {success && <div className="form-success" role="status">{success}</div>}
    <div className="form-field"><label htmlFor="contact-name">Your name <span aria-hidden="true">*</span></label><input id="contact-name" name="name" autoComplete="name" required aria-invalid={Boolean(errors.name)} aria-describedby={errors.name ? "contact-name-error" : undefined}/>{errors.name && <span className="field-error" id="contact-name-error">{errors.name}</span>}</div>
    <div className="form-field"><label htmlFor="contact-email">Email address <span aria-hidden="true">*</span></label><input id="contact-email" name="email" type="email" autoComplete="email" required aria-invalid={Boolean(errors.email)} aria-describedby={errors.email ? "contact-email-error" : undefined}/>{errors.email && <span className="field-error" id="contact-email-error">{errors.email}</span>}</div>
    <div className="form-field"><label htmlFor="contact-organization">Organization <span className="optional-label">Optional</span></label><input id="contact-organization" name="organization" autoComplete="organization" aria-invalid={Boolean(errors.organization)} aria-describedby={errors.organization ? "contact-organization-error" : undefined}/>{errors.organization && <span className="field-error" id="contact-organization-error">{errors.organization}</span>}</div>
    <div className="form-field"><label htmlFor="contact-message">What would you like to discuss? <span aria-hidden="true">*</span></label><textarea id="contact-message" name="message" rows={5} required minLength={20} maxLength={3000} aria-invalid={Boolean(errors.message)} aria-describedby={errors.message ? "contact-message-error" : "contact-message-help"}/>{errors.message ? <span className="field-error" id="contact-message-error">{errors.message}</span> : <span className="field-help" id="contact-message-help">At least 20 characters. Please don’t include confidential campaign material.</span>}</div>
    <div className="honeypot" aria-hidden="true"><label htmlFor="contact-website">Leave this field blank</label><input id="contact-website" name="website" tabIndex={-1} autoComplete="off"/></div>
    <button className="button button-primary" type="submit" disabled={pending}>{pending ? "Sending…" : "Send message"} </button>
    <p className="form-privacy-note">Your note is sent to the BrandLens team. See the <Link href="/privacy">privacy overview</Link>.</p>
  </form>;
}
