// Milestone 8 evidence: real-data screens + the SSE live-update proof.
import { chromium } from "playwright";

const out = process.argv[2] ?? "shots";
const BASE = "http://127.0.0.1:8787";

const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH || "/opt/pw-browsers/chromium",
});
const ctx = await browser.newContext({
  viewport: { width: 1280, height: 860 },
  baseURL: BASE,
});
const page = await ctx.newPage();
await page.request.post(`${BASE}/api/auth/login`, {
  data: { email: "jordan@meridian.demo", password: "rowhouse-ledger-26" },
});

async function shot(name, path) {
  if (path) {
    await page.goto(path, { waitUntil: "networkidle" });
    await page.waitForTimeout(500);
  }
  await page.screenshot({ path: `${out}/${name}.png` });
  console.log(`shot ${name}`);
}

await shot("m8-dashboard", "/");

// Live path: inject simulated transactions from a second context (no reload here).
const before = await page.locator("main").innerText();
await page.request.post(`${BASE}/api/dev/simulate-transactions`, { data: { count: 4 } });
await page.waitForTimeout(2500);
await shot("m8-dashboard-live");
const after = await page.locator("main").innerText();
console.log("live-update changed the page without reload:", before !== after);

await shot("m8-accounts", "/accounts");
await shot("m8-transactions", "/transactions");
await shot("m8-documents", "/documents");
await browser.close();
