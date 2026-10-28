// @vitest-environment jsdom
import { createElement } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { LanguageSelect, LocaleProvider, translate, useLocale, type Locale } from "./i18n";

function TranslatedLabel() {
  const { t } = useLocale();
  return createElement("p", null, t("auth.loginTitle"));
}

beforeEach(() => window.localStorage.clear());
afterEach(() => cleanup());

describe("BrandLens locale dictionaries", () => {
  it("provides Hindi and Marathi login labels", () => {
    expect(translate("hi", "auth.loginTitle")).toBe("अपने कार्यक्षेत्र में साइन इन करें");
    expect(translate("mr", "auth.loginTitle")).toBe("तुमच्या कार्यक्षेत्रात साइन इन करा");
  });

  it("falls back to English when a selected locale is missing a key", () => {
    const dictionaries: Record<Locale, unknown> = {
      en: { auth: { title: "English title" } },
      hi: { auth: {} },
      mr: { auth: {} },
    };
    expect(translate("hi", "auth.title", dictionaries)).toBe("English title");
    expect(translate("mr", "auth.missing", dictionaries)).toBe("auth.missing");
  });

  it("switches visible text immediately and restores the choice after remount", () => {
    const first = render(createElement(LocaleProvider, null, createElement(LanguageSelect), createElement(TranslatedLabel)));
    expect(screen.getByText("Sign in to your workspace")).toBeTruthy();
    fireEvent.change(screen.getByRole("combobox", { name: "Language" }), { target: { value: "hi" } });
    expect(screen.getByText("अपने कार्यक्षेत्र में साइन इन करें")).toBeTruthy();
    expect(window.localStorage.getItem("brandlens-locale")).toBe("hi");
    first.unmount();

    render(createElement(LocaleProvider, null, createElement(LanguageSelect), createElement(TranslatedLabel)));
    expect(screen.getByText("अपने कार्यक्षेत्र में साइन इन करें")).toBeTruthy();
    expect((screen.getByRole("combobox", { name: "भाषा" }) as HTMLSelectElement).value).toBe("hi");
  });
});
