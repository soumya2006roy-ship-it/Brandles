"use client";

import { useRef, useState, type ChangeEvent } from "react";

const MAX_DOCUMENT_BYTES = 5 * 1024 * 1024;

function formatBytes(bytes: number) {
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function OrganisationDocumentField() {
  const input = useRef<HTMLInputElement>(null);
  const [selected, setSelected] = useState<File | null>(null);
  const [error, setError] = useState("");

  function selectDocument(event: ChangeEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0] ?? null;
    if (!file) return;
    const extension = file.name.split(".").at(-1)?.toLocaleLowerCase();
    if (!extension || !["pdf", "png", "jpg", "jpeg"].includes(extension)) {
      event.currentTarget.value = "";
      setSelected(null);
      setError("Choose a PDF, PNG, or JPG document.");
      return;
    }
    if (file.size > MAX_DOCUMENT_BYTES) {
      event.currentTarget.value = "";
      setSelected(null);
      setError("The document must be 5 MB or smaller.");
      return;
    }
    setSelected(file);
    setError("");
  }

  function removeDocument() {
    if (input.current) input.current.value = "";
    setSelected(null);
    setError("");
  }

  return <div className="form-field"><label htmlFor="organisation-document">Supporting document <span className="field-help">Optional · PDF, PNG, or JPG · up to 5 MB</span></label><input ref={input} id="organisation-document" name="document" type="file" accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg" aria-describedby={error ? "organisation-document-help organisation-document-error" : "organisation-document-help"} aria-invalid={Boolean(error)} onChange={selectDocument}/><span className="field-help" id="organisation-document-help">Upload a document that helps verify the organisation.</span>{error && <span className="auth-message auth-error" id="organisation-document-error" role="alert">{error}</span>}{selected ? <div className="inline-actions" role="status"><span>{selected.name} · {formatBytes(selected.size)}</span><button className="small-button" type="button" onClick={removeDocument}>Remove</button></div> : <span className="field-help">No document selected.</span>}</div>;
}
