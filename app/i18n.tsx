"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useSyncExternalStore, type ReactNode } from "react";
import en from "./i18n/en.json";
import hi from "./i18n/hi.json";
import mr from "./i18n/mr.json";

export type Locale = "en" | "hi" | "mr";
const dictionaries = { en, hi, mr } as const;
type TranslationKey = string;
type LocaleContextValue = { locale: Locale; setLocale: (locale: Locale) => void; t: (key: TranslationKey) => string };
const LocaleContext = createContext<LocaleContextValue | null>(null);
const localeListeners = new Set<() => void>();

function getLocaleSnapshot(): Locale {
  if (typeof window === "undefined") return "en";
  const saved = window.localStorage.getItem("brandlens-locale");
  return saved === "hi" || saved === "mr" ? saved : "en";
}

function subscribeLocale(listener: () => void) {
  localeListeners.add(listener);
  window.addEventListener("storage", listener);
  return () => { localeListeners.delete(listener); window.removeEventListener("storage", listener); };
}

function lookup(dictionary: unknown, key: string): string | undefined {
  const value = key.split(".").reduce<unknown>((current, part) => current && typeof current === "object" ? (current as Record<string, unknown>)[part] : undefined, dictionary);
  return typeof value === "string" ? value : undefined;
}

export function translate(locale: Locale, key: string, dictionariesToUse: Record<Locale, unknown> = dictionaries): string {
  return lookup(dictionariesToUse[locale], key) ?? lookup(dictionariesToUse.en, key) ?? key;
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  const locale = useSyncExternalStore<Locale>(subscribeLocale, getLocaleSnapshot, () => "en");
  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);
  const setLocale = useCallback((next: Locale) => {
    window.localStorage.setItem("brandlens-locale", next);
    localeListeners.forEach((listener) => listener());
  }, []);
  const t = useCallback((key: string) => translate(locale, key), [locale]);
  const value = useMemo(() => ({ locale, setLocale, t }), [locale, setLocale, t]);
  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  const value = useContext(LocaleContext);
  if (!value) throw new Error("useLocale must be used within LocaleProvider");
  return value;
}

export function LanguageSelect({ className = "language-select" }: { className?: string }) {
  const { locale, setLocale, t } = useLocale();
  return <label className={className}><span className="visually-hidden">{t("language")}</span><select aria-label={t("language")} value={locale} onChange={(event) => setLocale(event.target.value as Locale)}><option value="en">{t("languages.en")}</option><option value="hi">{t("languages.hi")}</option><option value="mr">{t("languages.mr")}</option></select></label>;
}
