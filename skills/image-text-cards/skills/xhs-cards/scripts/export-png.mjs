#!/usr/bin/env node
// export-png.mjs — render each card to a 3x PNG (3240×4320).
// Usage: node scripts/export-png.mjs <run-dir>
// Card count is counted from the DOM — no constant to update.
// Uses playwright-core (not the MCP browser) to set deviceScaleFactor: 3.
import { pathToFileURL, fileURLToPath } from "node:url";
import { resolve } from "node:path";
import { mkdirSync } from "node:fs";
import { createRequire } from "node:module";

const runDir = resolve(process.argv[2] ?? ".");
// playwright-core resolves from the run dir (the skill repo ships no node_modules)
const require2 = createRequire(resolve(runDir, "package.json"));
const { chromium } = require2("playwright-core");
const OUT_DIR = resolve(runDir, "exports");
const HTML_URL = pathToFileURL(resolve(runDir, "dist/index.html")).href;

async function main() {
  mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1080, height: 1440 },
    deviceScaleFactor: 3,
  });
  const page = await context.newPage();
  await page.goto(HTML_URL, { waitUntil: "networkidle" });

  const ids = await page.evaluate(() =>
    Array.from(document.querySelectorAll("[data-card]"))
      .map((el) => el.getAttribute("data-card"))
      .filter(Boolean)
      .sort((a, b) => (Number(a) || 0) - (Number(b) || 0) || a.localeCompare(b))
  );
  if (ids.length === 0) throw new Error("no [data-card] elements found — is this a built deck?");

  for (const id of ids) {
    const el = page.locator(`[data-card="${id}"]`);
    const out = resolve(OUT_DIR, `${String(id).padStart(2, "0")}.png`);
    await el.screenshot({ path: out, type: "png" });
    console.log(`  ✓ ${id} → exports/${String(id).padStart(2, "0")}.png`);
  }
  await browser.close();
}
main().catch((e) => { console.error(e); process.exit(1); });
