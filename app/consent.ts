export const CONSENT_STORAGE_KEY = "brandlens-consent-v1";

export type ConsentChoice = {
  necessary: true;
  analytics: boolean;
  marketing: boolean;
  savedAt: string;
};

export function getConsent(): ConsentChoice | null {
  if (typeof window === "undefined") return null;
  try {
    const value = localStorage.getItem(CONSENT_STORAGE_KEY);
    if (!value) return null;
    const parsed = JSON.parse(value) as Partial<ConsentChoice>;
    if (parsed.necessary !== true || typeof parsed.analytics !== "boolean" || typeof parsed.marketing !== "boolean") return null;
    return { necessary: true, analytics: parsed.analytics, marketing: parsed.marketing, savedAt: parsed.savedAt ?? "" };
  } catch {
    return null;
  }
}

export function saveConsent(choice: Omit<ConsentChoice, "savedAt">) {
  localStorage.setItem(CONSENT_STORAGE_KEY, JSON.stringify({ ...choice, savedAt: new Date().toISOString() }));
  window.dispatchEvent(new Event("brandlens:consent-change"));
}
