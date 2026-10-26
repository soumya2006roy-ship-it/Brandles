import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("key public pages load with headings and security metadata", async ({ page }) => {
  for (const route of ["/", "/features", "/security", "/privacy"]) {
    await page.goto(route);
    await expect(page.locator("h1").first()).toBeVisible();
    await expect(page.locator('meta[name="description"]')).toHaveAttribute("content", /.+/);
    await expect(page.locator("body")).toBeVisible();
  }
});

test("demo is presented as a read-only sample workspace", async ({ page }) => {
  await page.goto("/demo");
  await expect(page.getByText("Read-only sample workspace", { exact: true }).first()).toBeVisible();
  await expect(page.getByText(/Changes and external model calls are disabled\./i)).toBeVisible();
});

test("key public pages have no automated axe violations", async ({ page }) => {
  for (const route of ["/", "/features", "/security", "/privacy"]) {
    await page.goto(route);
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
    expect(results.violations, `${route}: ${JSON.stringify(results.violations)}`).toEqual([]);
  }
});
