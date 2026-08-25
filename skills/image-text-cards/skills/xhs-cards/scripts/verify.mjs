#!/usr/bin/env node
// verify.mjs — the atomic audit: typecheck → build → DOM audits → pixel audits,
// one summary. Never re-assemble this chain by hand (piped commands swallow exit codes
// and audits then run on stale artifacts).
//
// Usage: node scripts/verify.mjs <run-dir>
// Optional: <run-dir>/plan/names.txt — proper nouns to assert never split (one per line).
import { pathToFileURL, fileURLToPath } from "node:url";
import { resolve, dirname } from "node:path";
import { existsSync, readFileSync, mkdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";

const runDir = resolve(process.argv[2] ?? ".");
const skillDir = dirname(dirname(fileURLToPath(import.meta.url)));
// playwright-core resolves from the run dir (the skill repo ships no node_modules)
const require2 = createRequire(resolve(runDir, "package.json"));
const { chromium } = require2("playwright-core");
const failures = [];
const ok = (m) => console.log(`  ✓ ${m}`);
const fail = (m) => { failures.push(m); console.log(`  ✗ ${m}`); };

function run(cmd, args, label) {
  const r = spawnSync([cmd, ...args].join(" "), { cwd: runDir, shell: true, encoding: "utf8" });
  if (r.status !== 0) { fail(`${label} failed`); console.log((r.stdout || "") + (r.stderr || "")); return false; }
  ok(label); return true;
}

async function main() {
  console.log(`verify: ${runDir}`);

  // 1. typecheck + build (hard stops)
  if (!run("npm", ["run", "typecheck"], "typecheck")) return finish();
  if (!run("npm", ["run", "build"], "build")) return finish();

  // 2. names for the split check — missing file is a failure (the audit silently
  //    no-ops without it; an empty file means "no proper nouns", which is valid)
  const namesFile = resolve(runDir, "plan/names.txt");
  if (!existsSync(namesFile)) {
    fail("plan/names.txt missing — write it (one proper noun per line; empty file if none) or the split-name audit is skipped silently");
  }
  const names = existsSync(namesFile)
    ? readFileSync(namesFile, "utf8").split(/\r?\n/).map((s) => s.trim()).filter(Boolean)
    : [];
  if (names.length > 0) ok(`split-name audit armed (${names.length} names)`);

  // 3. DOM audits + canonical 1x previews
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1440 } });
  await page.goto(pathToFileURL(resolve(runDir, "dist/index.html")).href, { waitUntil: "networkidle" });
  const ids = await page.evaluate(() =>
    Array.from(document.querySelectorAll("[data-card]")).map((el) => el.getAttribute("data-card")).filter(Boolean)
  );
  if (ids.length === 0) fail("no [data-card] elements found");
  ok(`cards found: ${ids.length}`);

  const dom = await page.evaluate(({ names }) => {
    const out = [];
    for (const id of document.querySelectorAll("[data-card]")) {
      const i = id.getAttribute("data-card");
      // square corners, asserted on the shell itself — element screenshots fill rounded
      // corners with an opaque page background, so pixel-alpha checks cannot catch this
      const br = getComputedStyle(id).borderRadius;
      if (br !== "0px") out.push(`card ${i}: shell borderRadius is "${br}" (must be 0 — rounded corners export as page-background-filled, not transparent)`);
      const cTop = id.getBoundingClientRect().top;
      const tk = id.querySelector("[data-takeaway]");
      const ft = id.querySelector("[data-footer]");
      if (ft && tk) {
        const gap = Math.round(ft.getBoundingClientRect().top - tk.getBoundingClientRect().bottom);
        if (gap <= 0) out.push(`card ${i}: takeaway overlaps footer (gap ${gap})`);
      }
      if (ft && !tk) {
        // takeaway-less cards (e.g. full-bleed screenshot pages): lowest content bottom vs footer top.
        // Leaf elements only (text lines, images, pills) — wrappers like an inset-0 content
        // div span the whole card and would false-positive. Skips decoration and footer subtree.
        let maxBottom = 0;
        for (const el of id.querySelectorAll("*")) {
          if (el.children.length > 0) continue;
          if (el.closest("[data-decor]") || el.closest("[data-footer]")) continue;
          const r = el.getBoundingClientRect();
          if (r.height > 0) maxBottom = Math.max(maxBottom, r.bottom);
        }
        const ftTop = ft.getBoundingClientRect().top;
        if (maxBottom > ftTop) out.push(`card ${i}: content (bottom ${Math.round(maxBottom)}) overlaps footer (top ${Math.round(ftTop)})`);
      }
      id.querySelectorAll("img").forEach((img) => {
        if (!img.complete || img.naturalWidth === 0) out.push(`card ${i}: broken image ${img.src.slice(-40)}`);
      });
      const walker = document.createTreeWalker(id, NodeFilter.SHOW_TEXT);
      const seen = new Set(); let n; // per-card: same text on another card is still audited
      while ((n = walker.nextNode())) {
        const t = n.textContent.trim();
        if (!t || seen.has(t)) continue; seen.add(t);
        const range = document.createRange(); range.selectNodeContents(n);
        const rects = Array.from(range.getClientRects()).filter((x) => x.width > 2);
        if (rects.length > 1) {
          const last = rects[rects.length - 1];
          if (last.width < rects[0].height * 1.2) out.push(`card ${i}: orphan wrap "${t.slice(0, 18)}…"`);
        }
        for (const name of names) {
          let idx = t.indexOf(name);
          while (idx !== -1) {
            const r2 = document.createRange(); r2.setStart(n, idx); r2.setEnd(n, idx + name.length);
            if (Array.from(r2.getClientRects()).filter((x) => x.width > 1).length > 1)
              out.push(`card ${i}: split name "${name}"`);
            idx = t.indexOf(name, idx + 1);
          }
        }
      }
    }
    return out;
  }, { names });
  dom.forEach(fail); if (dom.length === 0) ok("DOM audits (overflow/broken imgs/orphan wraps/split names)");

  // canonical 1x previews (deviceScaleFactor 1 context)
  mkdirSync(resolve(runDir, "preview"), { recursive: true });
  const pctx = await browser.newContext({ viewport: { width: 1080, height: 1440 }, deviceScaleFactor: 1 });
  const ppage = await pctx.newPage();
  await ppage.goto(pathToFileURL(resolve(runDir, "dist/index.html")).href, { waitUntil: "networkidle" });
  for (const id of ids) {
    await ppage.locator(`[data-card="${id}"]`).screenshot({ path: resolve(runDir, "preview", `${String(id).padStart(2, "0")}.png`) });
  }
  ok(`previews refreshed (${ids.length})`);
  await browser.close();

  // 4. pixel audits via PIL (void on previews; corners+size on exports) — python → py fallback
  const pyArgs = [resolve(skillDir, "scripts/pixel_audit.py"), runDir];
  let py = spawnSync("python", pyArgs, { encoding: "utf8" });
  if (py.error || py.status !== 0 && /can't open file|not recognized|无法打开/i.test((py.stderr || "") + (py.error ? String(py.error) : "")))
    py = spawnSync("py", pyArgs, { encoding: "utf8" });
  (py.stdout || "").trim().split(/\r?\n/).filter(Boolean).forEach((l) => { const t = l.trim(); t.startsWith("ok") ? ok(t.slice(2).trim()) : fail(t); });
  if (py.status !== 0) fail("python/PIL audit failed to run: " + (py.stderr || py.error || "").slice(0, 200));

  finish();
}

function finish() {
  console.log(failures.length === 0 ? "\nALL PASS" : `\n${failures.length} FAILURE(S)`);
  process.exit(failures.length === 0 ? 0 : 1);
}

main().catch((e) => { console.error(e); process.exit(1); });
