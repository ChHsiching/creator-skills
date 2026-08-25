# Pitfalls — verified failure modes

Each entry is a defect hit in production, with the fix the run verified. Read before Step 4 and whenever `verify.mjs` reports failures. Line-break defects live in [`typography.md`](typography.md); screenshot rules in [`card-anatomy.md`](card-anatomy.md).

## 1 — Emoji as icons

Emoji renders inconsistently across OSes and clashes with the palette. **Fix**: hand-authored SVG line icons (`stroke=currentColor`, 24×24, round caps). Grep card files for emoji ranges before review.

## 2 — Translationese

Word-by-word translation reads as coined, unnatural phrasing ("重新 pitch", "一手来源"). **Fix**: rewrite in natural target language from the translated fact base; keep commands, file names, product names in English. Read each line aloud — "would a native colleague say this?"

## 3 — Font sizes below the floor

Feed thumbnails are ~300px wide; text below the floors is illegible there. The authoritative floor table lives in [`card-anatomy.md`](card-anatomy.md) — check sizes against it, not against memory.

## 4 — Rounded container corners

The shell's `borderRadius` exports transparent PNG corners. **Fix**: `borderRadius: 0` on the shell; roundness lives inside cards (pills, blocks). Verify corners with PIL after export (verify.mjs does).

## 5 — Content overflows the footer

Dense cards push the last block onto the footer strip. **Fix**: compress real content — vertical lists → horizontal pills, gaps 12→8, merge items — keeping the plan's must-keeps. Never fix by shrinking fonts below floors.

## 6 — Outputs scattered; review handoff unclear

Screenshots and PNGs in the parent dir; preview/ littered with temp copies; user can't tell what to review. **Fix**: everything inside the run dir — `preview/` holds only canonical `NN.png` (1x), `exports/` only `NN.png` (3x); delete temp files before handing anything to the user and name the exact files to review.

## 7 — Images silently broken in the single-file build

A string `src="assets/x.png"` 404s after `vite-plugin-singlefile` hashes assets; the card collapses into a fake void. **Fix**: `import img from "../assets/x.png"`; verify.mjs checks `img.complete && naturalWidth > 0` on every card.

## 8 — Void: content crowds one half

Content piles in the top half with the takeaway stranded at the bottom (or the mirror). **Fix**: add a visual block or restructure distribution — density fills the canvas; enlarging gaps scatters it with no center of gravity. verify.mjs flags it (threshold defined in `scripts/pixel_audit.py`).

## 9 — Verification ran on stale artifacts

A piped command (`npm run typecheck | tail`) swallows the failure code; audits then run on the previous build and "pass". **Fix**: `scripts/verify.mjs` runs typecheck → build → audits as one atomic sequence with a single pass/fail summary; never re-assemble the chain by hand.

## 10 — Unauthorized edits during user feedback rounds

Fixing a named item while also "improving" adjacent copy burns trust. **Fix**: confirm understanding of the request and the exact operation list before touching files; change only what the user named; surface adjacent findings as suggestions for the user to decide.
