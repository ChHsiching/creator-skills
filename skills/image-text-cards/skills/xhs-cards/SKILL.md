---
name: xhs-cards
description: "Turn any link, file, or pasted text into a set of 3:4 Xiaohongshu (小红书) image cards, each rendered to a 3x PNG, plus the caption. Use when the user wants 小红书图文/卡片组/竖屏图文笔记, asks to turn an article/changelog/update into shareable image pages, or mentions xhs-cards/小红书卡片."
---

# xhs-cards

Turn source material into a deck of N standalone 3:4 cards (1080×1440 CSS canvas → 3240×4320 PNG), designed freely inside the card framework on a reacticle theme, plus a Xiaohongshu caption. Standalone: no other skill's pipeline is invoked. The user reviews **once**, at the end, on the complete deck.

**Dependencies** (assumed installed): `no-ai-slop` skill (copy review, Step 6); npm + Node 18+ (reacticle workspace); `playwright-core` with a chromium (render + audit); Python PIL (pixel audits).

## What you produce

1. `exports/NN.png` — the cards, 3240×4320 each
2. `caption.md` — titles, body, pinned comment, chapters, hashtags, sources
3. `source/source.md`, `plan/plan.md`, `article/` (React + reacticle deck workspace)

## Pipeline

### Step 1 — Source, chased until sufficient

Create the run dir; every path below (`source/`, `plan/`, `article/`, …) lives inside it. Extract the material into `source/source.md`. Web inputs: fetch with the environment's page-fetch tool first; on 404 or empty (JS-rendered pages) retry with a rendering fetcher. Files/paste: convert directly.

**Sufficiency rule**: links inside the source (repos, gists, docs, APIs) are part of the fact base — fetch and verify each one that the deck will make claims about, and cross-check the source's own claims against them. Write uncertain items to `source/extraction-notes.md`. If target language ≠ source language, produce a natural translation as the fact base.

**Done when** every number, name, command, and quote that will appear on a card traces to source.md or a chased link — not to memory.

### Step 2 — Plan the deck, then Checkpoint 1

Write `plan/plan.md`: Brief (audience, tone, key claims, target language) + card list (each card: core idea + visual approach) + theme pick + assets policy. Read [`references/themes.md`](references/themes.md) before choosing a theme.

Self-check the plan, then stop and collect user decisions independently (the environment's question/confirmation tool, one question each; recommend, never silently choose):

1. **Card count** — 8 condensed / 11 medium / 14 full, by information volume
2. **Theme** — recommendation must argue **content fit first** (how the theme's character maps to this material); engineering convenience may appear only as a second, labeled reason
3. **Density** — how much source detail to keep (~50% briefing / ~90% tutorial-style)

**Done when** the user has answered every question. Plan-rules: no card may reference content a later card reveals (forward references), and no card may preview a later card's payoff — narrative order is part of the plan check. Also write `plan/names.txt` — every proper noun that must never wrap across lines (product/repo/command names), one per line, **empty file if none**: verify.mjs fails when the file is missing, because the split-name audit silently no-ops without it.

### Step 3 — Scaffold the deck

```bash
bash <skill>/scripts/scaffold-deck.sh <run-dir> --theme=<id>
```

Creates a Vite + React + TS workspace born deck-shaped: `article/` holds `Deck.tsx`, `Card.tsx`, `cards/_shared.tsx`, one file per card; `index.html` already loads the theme's fonts; memory dirs `source/ plan/ preview/ exports/` created (the run dir may already hold `source/`/`plan/` from Steps 1–2 — the scaffold allows that and only refuses an already-scaffolded workspace). Verify with `npm run typecheck && npm run build`.

**Done when** the empty workspace typechecks and builds.

### Step 4 — Design all cards, freely inside the framework

Read [`references/card-anatomy.md`](references/card-anatomy.md) (canvas contract, font floors, anchors) and [`references/typography.md`](references/typography.md) (line-break discipline) before writing, and again whenever layout questions come up.

The design stance: the framework (canvas, floors, anchors, audit hooks) is fixed; **everything visual is designed fresh for this material** — layouts, typography pairings, decorative language come from the theme's character and the content. `assets/samples/` holds finished-deck samples for inspiration only ([`references/card-anatomy.md`](references/card-anatomy.md) states the stance in full).

Screenshots embedded in cards: the screenshot's aspect ratio is fixed by its content — fit the layout to the screenshot (position/size only), and if it cannot fit legibly, give it its own page with page furniture dropped. Crop at element boundaries, mid-element cuts are defects.

**Done when** every planned card exists, the deck typechecks and builds.

### Step 5 — Self-audit loop (no user time spent)

Run `node <skill>/scripts/verify.mjs <run-dir>` — the atomic audit (typecheck → build → DOM + pixel checks; the full audit table lives in [`references/export.md`](references/export.md)). Fix, re-run, until the report is all-pass.

**Done when** verify reports zero failures.

### Step 6 — Two review loops, then final review

- **Typography loop** (rules: [`references/typography.md`](references/typography.md)): a subagent reviews all cards' rendered text — semantic line breaks, orphan lines, split names, mono/ASCII mixing, ink fill — returns fail items, you fix, re-review, until clean.
- **Copy loop** (dependency: `no-ai-slop`): a subagent runs no-ai-slop **detect** on all card copy + caption drafts, names patterns with quoted lines; you fix, re-detect, until clean.

Then a final-review subagent over the whole deck: editorial (facts vs source.md, verbatim quotes), visual (theme discipline, weight), technical (anchors, build), **audience (cold reader: title/comprehensible without context; no jargon only a deck-reader knows)**. Fix everything it flags, re-verify.

**Done when** both loops report clean and final review flags are fixed and re-audited.

### Step 7 — Render and caption

`node <skill>/scripts/export-png.mjs <run-dir>` renders every card at 3x (card count auto-detected). Write `caption.md` per [`references/caption-spec.md`](references/caption-spec.md) — every count and the cold-reader title test live there; the caption text also goes through the no-ai-slop detect pass (same loop as Step 6). Re-run verify after export (it checks dimensions and corners).

**Done when** exports/ holds N 3240×4320 PNGs with opaque corners, and every caption field passes its spec check.

### Step 8 — One consolidated review

Present the complete deck to the user: preview paths (`preview/` holds only canonical `NN.png` — the hygiene rule lives in [`references/export.md`](references/export.md)), caption, verification summary. User feedback rounds: **confirm your understanding of the request and the exact operations before touching files**; change only what the user named, list adjacent observations as suggestions for them to decide.

**Done when** the user accepts.

## Failure modes

[`references/pitfalls.md`](references/pitfalls.md) — the recurring defects (voids, footer overlap, emoji icons, translationese, scattered outputs) with the verified fix for each. Read before Step 4 and whenever verify fails.
