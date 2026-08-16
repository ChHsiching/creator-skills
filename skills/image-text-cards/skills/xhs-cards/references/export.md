# Export and verification

The render and verification scripts for Steps 7–8. Each is verified in production.

## 3x render script (`scripts/export-png.mjs`)

Render each card to a 3240×4320 PNG (3x of the 1080×1440 CSS canvas). Use Playwright via `playwright-core` (globally available via `require`), not the MCP Playwright browser — the MCP browser cannot change its `deviceScaleFactor` after launch, and a standalone launch is the only way to set 3x.

```js
import { chromium } from "playwright-core";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";
import { mkdirSync } from "node:fs";

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
}
main().catch(e => { console.error(e); process.exit(1); });
```

Run after `npm run build` produces `dist/index.html`. The script lives in the card workspace root; `N` is the card count.

## Corner verification (square, not rounded)

After export, verify every PNG's four corners are opaque — `borderRadius: 0` on the Card shell should produce fully opaque corners. This catches pitfall 4 if it regresses.

```python
from PIL import Image
import glob
bad = []
for f in sorted(glob.glob("exports/*.png")):
    im = Image.open(f).convert("RGBA")
    w, h = im.size
    corners = [im.getpixel((2,2))[3], im.getpixel((w-3,2))[3],
               im.getpixel((2,h-3))[3], im.getpixel((w-3,h-3))[3]]
    if any(a != 255 for a in corners):
        bad.append(f)
print("all square" if not bad else f"rounded: {bad}")
```

## Layout measurement (Step 7 — overflow and void)

### Overflow check

Measure every card's Takeaway bottom against its footer top. The Takeaway is found by its theme-accent background color — read the RGB from `node_modules/reacticle/src/theme/themes/<id>/<id>.css`. For andy: `#ff7e1d` = `rgb(255, 126, 29)`.

```js
// Playwright evaluate — run for i = 1..N
const card = document.querySelector(`section[data-card="${i}"]`);
const footer = card.querySelector("footer");
const footerTop = Math.round(footer.getBoundingClientRect().top - card.getBoundingClientRect().top);
const takeaway = Array.from(card.querySelectorAll("div"))
  .find(d => window.getComputedStyle(d).backgroundColor === "rgb(255, 126, 29)");
const gap = footerTop - Math.round(takeaway.getBoundingClientRect().bottom - card.getBoundingClientRect().top);
// gap > 0: pass. gap < 0: overlap → compress layout (pitfall 5).
```

Run for all N cards, not just the ones that look risky — the run found cards 12 and 14 overlapping while the rest were fine.

### Void check

Screenshot every card and eyeball it. The automated assist measures whether content occupies only the top half:

```js
// Find the Takeaway top, then the bottom of the last content block above it.
// If the gap between them is large, the card has a void (pitfall 8).
const blocks = [...card.querySelectorAll("*")].filter(el => {
  const txt = (el.textContent || "").trim();
  const r = el.getBoundingClientRect();
  return txt.length > 3 && r.height > 8 && !el.getAttribute("aria-hidden")
         && !el.closest("footer") && el.tagName !== "FOOTER";
});
const takeawayTop = /* Takeaway's top, from the overflow check above */;
const lastContentBottom = Math.max(...blocks
  .filter(b => b.getBoundingClientRect().bottom < takeawayTop)
  .map(b => b.getBoundingClientRect().bottom - card.getBoundingClientRect().top));
const voidGap = takeawayTop - lastContentBottom;
// voidGap large (roughly > 150px on the 1080-wide canvas) → void.
// Fix: add a visual block or restructure distribution (enlarging gaps produces scatter).
```

The void check is primarily visual — the DOM measurement is a backstop. When in doubt, screenshot and look: if hiding the Takeaway leaves an obvious empty lower half, the card has a void.

## Dimension verification

Confirm the export is truly 3x:

```python
from PIL import Image
im = Image.open("exports/01.png")
assert im.size == (3240, 4320), f"expected 3240x4320, got {im.size}"
```
