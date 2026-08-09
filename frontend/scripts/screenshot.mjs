// Dev tool: screenshot key views against a running backend (127.0.0.1:8787).
// Usage: node scripts/screenshot.mjs <outdir>
import { chromium } from "playwright";

const out = process.argv[2] ?? "shots";
const BASE = "http://127.0.0.1:8787";

const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH || "/opt/pw-browsers/chromium",
});

async function shoot(name, { width = 1280, height = 860, dark = false, mobile = false,
                             loggedIn = false, path = "/" } = {}) {
  const ctx = await browser.newContext({
    viewport: mobile ? { width: 375, height: 720 } : { width, height },
    colorScheme: dark ? "dark" : "light",
    baseURL: BASE,
  });
  const page = await ctx.newPage();
  if (loggedIn) {
    await page.request.post(`${BASE}/api/auth/login`, {
      data: { email: "jordan@meridian.demo", password: "rowhouse-ledger-26" },
    });
  }
  await page.goto(path, { waitUntil: "networkidle" });
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${out}/${name}.png`, fullPage: false });
  await ctx.close();
  console.log(`shot ${name}`);
}

await shoot("welcome-light");
await shoot("welcome-dark", { dark: true });
await shoot("shell-light", { loggedIn: true, path: "/transactions" });
await shoot("shell-dark", { loggedIn: true, dark: true, path: "/transactions" });
await shoot("shell-mobile", { loggedIn: true, mobile: true, path: "/" });
await browser.close();
