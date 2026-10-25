import { getConsent } from "@/app/consent";

export type TrackingEvents = {
  cta_click: { label: string; href: string };
  demo_started: { scenario: "skincare-campaign" };
  demo_scan_run: { scanNumber: number };
  demo_approved: { version: string };
  contact_submit_success: { source: "contact-form" };
  contact_submit_error: { source: "contact-form"; reason: "validation" | "delivery" | "network" };
  scroll_75: { path: string };
};

export function track<EventName extends keyof TrackingEvents>(event: EventName, payload: TrackingEvents[EventName]) {
  if (typeof window === "undefined" || getConsent()?.analytics !== true) return;
  window.dispatchEvent(new CustomEvent("brandlens:track", { detail: { event, payload, at: new Date().toISOString() } }));
}
