const origin = (process.env.BRANDLENS_SITE_URL ?? "http://127.0.0.1:3000").replace(/\/$/, "");
const routes = [
  "/", "/problem", "/how-it-works", "/campaign-consistency-graph", "/features", "/roles",
  "/security", "/roadmap", "/contact", "/privacy", "/cookies", "/login", "/sign-up", "/signup", "/org/create", "/join",
  "/verify-email", "/forgot-password", "/reset-password", "/app", "/app/invite",
  "/app/organisations/new", "/app/admin/verifications", "/app/account/sessions",
];
const failures = [];
const visited = new Set();

async function inspect(path) {
  if (visited.has(path)) return;
  visited.add(path);
  try {
    const response = await fetch(new URL(path, origin), { redirect: "follow" });
    if (response.status >= 400) {
      failures.push(`${path}: HTTP ${response.status}`);
      return;
    }
    const html = await response.text();
    for (const [, href] of html.matchAll(/\bhref="([^"]+)"/g)) {
      if (!href.startsWith("/") || href.startsWith("//") || href.startsWith("/#")) continue;
      const target = new URL(href, origin);
      await inspect(`${target.pathname}${target.search}`);
    }
  } catch (error) {
    failures.push(`${path}: ${error instanceof Error ? error.message : String(error)}`);
  }
}

for (const route of routes) await inspect(route);
for (const path of ["/robots.txt", "/sitemap.xml", "/manifest.webmanifest", "/favicon.ico", "/icon.svg", "/icon-192.png", "/icon-512.png", "/maskable-icon-512.png", "/apple-touch-icon.png"]) {
  try {
    const response = await fetch(new URL(path, origin), { redirect: "follow" });
    if (response.status >= 400) failures.push(`${path}: HTTP ${response.status}`);
  } catch (error) {
    failures.push(`${path}: ${error instanceof Error ? error.message : String(error)}`);
  }
}
try {
  const retired = await fetch(new URL("/demo", origin), { redirect: "manual" });
  if (retired.status !== 404) failures.push(`/demo: expected HTTP 404, got ${retired.status}`);
  const sitemap = await fetch(new URL("/sitemap.xml", origin));
  if ((await sitemap.text()).toLowerCase().includes("/demo")) failures.push("/sitemap.xml: retired route is listed");
} catch (error) { failures.push(`/demo/sitemap check: ${error instanceof Error ? error.message : String(error)}`); }

if (failures.length) {
  console.error(`Checked ${visited.size} internal routes; ${failures.length} failed:`);
  console.error(failures.join("\n"));
  process.exitCode = 1;
} else {
  console.log(`Checked ${visited.size} internal routes and required metadata assets: all returned below HTTP 400.`);
}
