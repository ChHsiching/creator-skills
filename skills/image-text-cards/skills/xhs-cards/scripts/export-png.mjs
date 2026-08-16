#!/usr/bin/env node
// export-png.mjs — render each card to a 3x PNG (3240×4320).
// Run after `npm run build`. Uses playwright-core (not the MCP browser) to set deviceScaleFactor: 3.
// See references/export.md.
import { chromium } from "playwright-core";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";
import { mkdirSync } from "node:fs";

const N = 14; // ← set to the card count
const OUT_DIR = resolve("exports");
const HTML_URL = pathToFileURL(resolve("dist/index.html")).href;

async function main() {
  mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1080, height: 1440 },
    deviceScaleFactor: 3,
  });
  const page = await context.newPage();
  await page.goto(HTML_URL, { waitUntil: "networkidle" });

  for (let i = 1; i <= N; i++) {
    const out = resolve(OUT_DIR, `${String(i).padStart(2, "0")}.png`);
    await page.locator(`section[data-card="${i}"]`).screenshot({ path: out, type: "png" });
    console.log(`  ✓ ${i}/${N} → exports/${String(i).padStart(2, "0")}.png`);
  }
  await browser.close();
  console.log("done");
}
main().catch((e) => { console.error(e); process.exit(1); });
