// Drive the Documents upload → preview → import flow through the real UI.
import { chromium } from "playwright";

const out = process.argv[2] ?? "shots";
const BASE = "http://127.0.0.1:8787";
const PDF = "../sample_data/jordan/statements/american_bank/checking_4417_2025-11.pdf";

const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH || "/opt/pw-browsers/chromium",
});
const page = await (await browser.newContext({
  viewport: { width: 1280, height: 900 }, baseURL: BASE,
})).newPage();

await page.request.post(`${BASE}/api/auth/login`, {
  data: { email: "jordan@meridian.demo", password: "rowhouse-ledger-26" },
});
await page.goto("/documents", { waitUntil: "networkidle" });

await page.setInputFiles('input[type="file"]', PDF);
await page.waitForSelector("text=uploaded", { timeout: 15000 });
await page.click('table button:has-text("checking_4417_2025-11.pdf")');
await page.waitForSelector("text=transactions found", { timeout: 20000 });
await page.screenshot({ path: `${out}/m8-doc-preview.png` });
console.log("preview rendered");

await page.click('button:has-text("Import")');
await page.waitForSelector("text=/Imported \\d+ transaction/", { timeout: 20000 });
await page.screenshot({ path: `${out}/m8-doc-imported.png` });
const status = await page.locator('[role="status"]').last().innerText();
console.log("import result:", status);
await browser.close();
