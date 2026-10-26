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

test("account entry points expose real sign-in and organisation flows", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/sign in|log in/i);
  await expect(page.getByLabel(/email/i)).toBeVisible();
  await page.goto("/sign-up");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/create|register/i);
  await expect(page.getByLabel(/password/i)).toBeVisible();
});

test("theme button switches its icon between sun and moon", async ({ page }) => {
  await page.goto("/");
  const toggle = page.getByRole("button", { name: "Switch to dark mode" });
  await expect(toggle).toHaveText("☀️");
  await toggle.click();

  const switchToLight = page.getByRole("button", { name: "Switch to light mode" });
  await expect(switchToLight).toHaveText("🌙");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await switchToLight.click();
  await expect(page.getByRole("button", { name: "Switch to dark mode" })).toHaveText("☀️");
});

test("contact form shows validation feedback and shared rate limit returns Retry-After", async ({ page, request }) => {
  await page.goto("/contact");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.locator(".form-error-summary")).toContainText("Check the highlighted fields");

  const octet = Math.floor(Math.random() * 200) + 20;
  const results = [];
  for (let index = 0; index < 6; index += 1) {
    results.push(await request.post("/api/contact", {
      headers: { "x-real-ip": `198.51.100.${octet}`, "x-forwarded-for": `203.0.113.${index + 1}` },
      data: { name: "Test Person", email: "test@example.test", organization: "", message: "A valid but unconfigured test submission." },
    }));
  }
  expect(results.slice(0, 5).every((response) => response.status() === 503)).toBe(true);
  expect(results[5].status()).toBe(429);
  expect(Number(results[5].headers()["retry-after"])).toBeGreaterThan(0);
});

test("key public pages have no automated axe violations", async ({ page }) => {
  for (const route of ["/", "/features", "/security", "/privacy"]) {
    await page.goto(route);
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
    expect(results.violations, `${route}: ${JSON.stringify(results.violations)}`).toEqual([]);
  }
});
