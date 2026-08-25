# Verification and export

Two scripts own this layer. Both are run against a built deck (`dist/index.html`); neither needs hand-tuned constants.

## `scripts/verify.mjs <run-dir>` — the atomic audit

Runs, in order — typecheck and build are hard stops, later audits continue to collect failures. Emits one summary (all-pass, or the failure list). The audits:

| Audit | Method |
|---|---|
| Overflow | `data-takeaway` bottom vs `data-footer` top, gap > 0; on takeaway-less cards the last content block's bottom vs footer top |
| Void | pixel scan per card: largest continuous empty band above the threshold flags (implementation and threshold live in `scripts/pixel_audit.py`) |
| Orphan line wraps | per text node: last line width < ~1 char → flag (Range rects) |
| Split proper nouns | substring-level Range check over configured names (product/repo/command strings from the deck's plan) |
| Broken images | `img.complete && naturalWidth > 0` on every card |
| Square corners | every card shell's computed `border-radius` must be `0px` (DOM assertion — element screenshots fill rounded corners with an opaque page background, so pixel-alpha checks cannot catch this) |
| Export size (if exports/ exists) | every PNG 3240×4320 (`scripts/pixel_audit.py`) |

External vision-model tools (if the environment has one) are **assist only** — known flaky in practice. Decisions come from the deterministic checks above; look at screenshots with your own eyes before user handoff.

## `scripts/export-png.mjs <run-dir>` — 3x render

Playwright via `playwright-core`, `deviceScaleFactor: 3`, viewport 1080×1440; screenshots each `[data-card]` element to `exports/NN.png`. Card set is **taken from the DOM** (every `[data-card]` found, sorted; missing indices skipped) — no constant to update when the deck grows or shrinks.

After export, re-run verify.mjs (its export-set checks cover dimensions and corners).

## Preview hygiene

`verify.mjs` refreshes canonical 1x `NN.png` previews into `preview/` on every run — that directory holds those and nothing else. Temp comparison copies live nowhere: create, use, delete. User handoff names the exact files to review.
