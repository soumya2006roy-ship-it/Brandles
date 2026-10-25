"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { getConsent, saveConsent, type ConsentChoice } from "@/app/consent";
import { track } from "@/app/track";

function subscribe(callback: () => void) {
  window.addEventListener("brandlens:consent-change", callback);
  window.addEventListener("storage", callback);
  return () => {
    window.removeEventListener("brandlens:consent-change", callback);
    window.removeEventListener("storage", callback);
  };
}

function getSnapshot() {
  try {
    return localStorage.getItem("brandlens-consent-v1");
  } catch {
    return null;
  }
}

function getServerSnapshot() {
  return null;
}

export function PrivacyConsentProvider({ children }: { children: React.ReactNode }) {
  const raw = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const consent: ConsentChoice | null = raw ? getConsent() : null;
  const [open, setOpen] = useState(false);
  const [customizing, setCustomizing] = useState(false);
  const [analytics, setAnalytics] = useState(false);
  const [marketing, setMarketing] = useState(false);
  const [savedMessage, setSavedMessage] = useState("");

  useEffect(() => {
    if (!savedMessage) return;
    const timeout = window.setTimeout(() => setSavedMessage(""), 4200);
    return () => window.clearTimeout(timeout);
  }, [savedMessage]);

  useEffect(() => {
    function showPreferences() {
      const current = getConsent();
      setAnalytics(current?.analytics ?? false);
      setMarketing(current?.marketing ?? false);
      setCustomizing(true);
      setOpen(true);
    }
    window.addEventListener("brandlens:open-consent", showPreferences);
    return () => window.removeEventListener("brandlens:open-consent", showPreferences);
  }, []);

  useEffect(() => {
    if (!consent?.analytics) return;
    let sent = false;
    const checkScroll = () => {
      if (sent) return;
      const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
      if (maxScroll > 0 && window.scrollY / maxScroll >= 0.75) {
        sent = true;
        track("scroll_75", { path: window.location.pathname });
      }
    };
    window.addEventListener("scroll", checkScroll, { passive: true });
    checkScroll();
    return () => window.removeEventListener("scroll", checkScroll);
  }, [consent?.analytics, raw]);

  function chooseAll(enabled: boolean) {
    saveConsent({ necessary: true, analytics: enabled, marketing: enabled });
    setOpen(false);
    setCustomizing(false);
    setSavedMessage(enabled ? "Your preferences are saved. Optional categories are enabled." : "Your preferences are saved. Optional categories are off.");
  }

  function saveCustom() {
    saveConsent({ necessary: true, analytics, marketing });
    setOpen(false);
    setCustomizing(false);
    setSavedMessage("Your cookie preferences are saved.");
  }

  return <>{children}<div className="consent-region">{!consent || open ? <section className="consent-panel" aria-labelledby="consent-title" aria-describedby="consent-description"><div className="consent-copy"><p className="eyebrow">Your privacy choices</p><h2 id="consent-title">Cookies, on your terms.</h2><p id="consent-description">Necessary storage remembers this choice. Optional analytics and marketing stay off until you allow them.</p></div>{customizing && <div className="consent-options"><label className="consent-option"><input type="checkbox" checked disabled/><span><strong>Necessary</strong><small>Core features and your privacy choice</small></span><em>Always on</em></label><label className="consent-option"><input type="checkbox" checked={analytics} onChange={(event) => setAnalytics(event.target.checked)}/><span><strong>Analytics</strong><small>Measure site use and interactions</small></span></label><label className="consent-option"><input type="checkbox" checked={marketing} onChange={(event) => setMarketing(event.target.checked)}/><span><strong>Marketing</strong><small>Optional campaign measurement</small></span></label></div>}<div className="consent-actions">{customizing ? <><button className="button button-primary" type="button" onClick={saveCustom}>Save preferences</button><button className="consent-text-button" type="button" onClick={() => setCustomizing(false)}>Back</button></> : <><button className="button button-primary" type="button" onClick={() => chooseAll(true)}>Accept all</button><button className="button consent-secondary" type="button" onClick={() => chooseAll(false)}>Reject optional</button><button className="consent-text-button" type="button" onClick={() => { setAnalytics(consent?.analytics ?? false); setMarketing(consent?.marketing ?? false); setCustomizing(true); }}>Customise</button></>}{consent && <button className="consent-close" type="button" aria-label="Close cookie preferences" onClick={() => setOpen(false)}>×</button>}</div></section> : savedMessage && <div className="consent-saved" role="status">{savedMessage}</div>}</div></>;
}

export function openCookiePreferences() {
  window.dispatchEvent(new Event("brandlens:open-consent"));
}
