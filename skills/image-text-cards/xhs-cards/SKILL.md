---
name: xhs-cards
description: "Turn any link, file, or pasted text into a set of 3:4 Xiaohongshu (小红书) image cards, each rendered to a 3x PNG. Use when the user wants 小红书图文/卡片组/竖屏图文笔记, asks to turn an article/changelog/update into shareable image pages, or mentions xhs-cards/小红书卡片."
---

# xhs-cards

A **router** over [`beautiful-article`](../beautiful-article/SKILL.md): beautiful-article owns source extraction, editorial planning, theme system, and scaffold. This skill takes over at the card layer — reshaping the article into a deck of 3:4 cards, rendering each to a 3x PNG, and writing the caption.

## What you produce

1. `exports/NN.png` — the cards, each 3240×4320 (3x of 1080×1440)
2. `caption.md` — Xiaohongshu titles, body, pinned comment, chapter list, hashtags, sources
3. `source/source.md` + `plan/plan.md` — from beautiful-article Phases 1–2
4. `article/` — the React + reacticle workspace (Deck + Card + cards/NN-*.tsx)

## The pipeline

### Step 1–3 — Run beautiful-article's editorial process

Follow beautiful-article's SKILL.md for Phase 0 through Phase 3 Checkpoint 1 — source extraction, editorial plan, and the five-decision Checkpoint 1. This skill only changes two things in those phases:

- **Phase 0–1, URL inputs**: try WebFetch first; on 404 (JS-rendered sites), fall back to `mcp__chhsich-web-fetch__fetch` with `return_format: markdown`.
- **Phase 2, Outline**: the plan is a **card list** (N cards, each with its core idea + visual technique), flowing as a deck rather than article sections.
- **Phase 3, Checkpoint 1**: the five decisions stay independent, but two take card-deck-specific options — card count (condensed 8 / medium 11 / full 14, recommend by information volume) and theme (warm themes suit Xiaohongshu: andy, freddie, sottsass).

**Done when** Checkpoint 1 passes (all decisions confirmed by the user).

### Step 4 — Scaffold, then reshape into a card deck

Run `beautiful-article/scripts/scaffold.sh <dir> --theme=<id>`. Then make the structural cut that defines this skill: delete the flowing-article scaffold (`article/Article.tsx`, `article/Cover.tsx`, `article/sections/`) and replace it with a card deck — rewrite `main.tsx` to a `<Deck/>`, create `Card.tsx` (shared shell), `cards/_shared.tsx` (shared typography + Icon), and one file per card (`cards/NN-*.tsx`).

Read [`references/card-anatomy.md`](references/card-anatomy.md) for the Card shell spec, the shared typography component, the Icon system, and the visual-technique repertoire — all verified in production. The templates in [`assets/`](../assets/) encode the same specs as ready-to-copy files.

**Done when** the workspace typechecks and renders the first three cards (cover + overview + one representative) without error.

### Step 5 — First Spread, then Checkpoint 2

Build cover + overview + one representative card. Screenshot them into `preview/` (a subdirectory — keep all output inside the card workspace). Hand to a First Spread Reviewer subagent. Run Checkpoint 2 (acceptance + development mode A/B) — two independent questions.

The first spread is the quality gate. The user will notice three things first: font size (readable in a ~300px feed thumbnail), cover design (a card worth opening), copy (natural, the way a colleague would say it). Read [`references/pitfalls.md`](references/pitfalls.md) before this step — its eight failure modes were all surfaced and fixed in production, and the first spread is where most of them show up.

**Done when** the user accepts the first spread and picks a development mode.

### Step 6 — Build all cards

Write every card. Each has a title, a lead, a visual block (the idea shown, told only as backup), and a Takeaway (one line at the bottom). Every card earns a visual technique — flow diagram, compare panel, mapping row, stat pill, process chain — chosen to serve that card's core idea. The verified repertoire is in [`references/card-anatomy.md`](references/card-anatomy.md).

**Visual weight is the core quality standard.** A 3:4 card is a fixed 1440px canvas. Content fills it by density: two failure modes both make the card look broken — content piled in the top half leaving a void below, or elements forced apart with large gaps to fake fullness. The fix for either is adding visual blocks or restructuring the distribution; [`references/pitfalls.md`](references/pitfalls.md) pitfall 8 has the concrete techniques verified this run (split-screen cover, layer cards, enlarged anchor text, expanded lists).

**Done when** every card exists and the deck typechecks — Step 7 then verifies the layout.

### Step 7 — Layout verification (both directions)

A card fails two ways: overflow (content spills past the footer) and void (content occupies only the top half). Check both, on every card.

Use Playwright `evaluate` to measure each card's Takeaway bottom against its footer top — the overflow detector finds the Takeaway by its theme-accent background color (read the RGB from the theme's CSS in `node_modules/reacticle/`). Screenshot every card to read its visual weight — if hiding the Takeaway mentally leaves an obvious empty lower half, the card has a void. The exact scripts are in [`references/export.md`](references/export.md).

Fix overflow by compressing layout — the verified techniques are in [`references/pitfalls.md`](references/pitfalls.md) pitfall 5. Fix a void by adding a visual block or restructuring the distribution — pitfall 8 has the verified fill techniques.

**Done when** every card passes: the overflow gap is positive on all N cards, and the screenshots show no voids.

### Step 8 — Render to 3x PNG

Build the single-file HTML (`npm run build`), then render each card via Playwright at `deviceScaleFactor: 3` — CSS canvas 1080×1440 becomes PNG 3240×4320. Use the standalone render script (Playwright via `playwright-core`, which lets you set the device scale factor; the MCP browser cannot change its scale after launch). Verify every PNG's four corners are opaque (alpha 255) — square corners. Read [`references/export.md`](references/export.md) for the render script and the corner-verification script.

**Done when** every card is a clean 3240×4320 PNG with square corners, in `exports/`.

### Step 9 — Caption

Write `caption.md` following [`references/caption-spec.md`](references/caption-spec.md) — Xiaohongshu titles (≤20 chars), body (≤100 chars), pinned comment (≤300 chars including spaces and punctuation), chapter list (two versions), hashtags, sources. Verify every character count with `len()` before delivery. Write in a professional tone.

**Done when** caption.md exists with all character counts verified.

### Step 10 — Final review and delivery

Run a Final Reviewer subagent across all cards (editorial / visual / technical). Fix what it flags, then run Checkpoint 3 (delivery confirmation) — an independent question.

**Done when** the user confirms delivery.

## References

| File | Read when |
|---|---|
| [`references/card-anatomy.md`](references/card-anatomy.md) | Step 4 (building the deck) and Step 6 (choosing visual techniques) — Card shell, shared typography, Icon, visual repertoire |
| [`references/pitfalls.md`](references/pitfalls.md) | Before Step 5 (first spread) and Step 7 (layout verification) — the eight verified failure modes and their fixes |
| [`references/export.md`](references/export.md) | Step 7 (layout measurement scripts) and Step 8 (render + corner verification) |
| [`references/caption-spec.md`](references/caption-spec.md) | Step 9 — caption structure and character limits |

The templates in [`assets/`](assets/) (`Card.template.tsx`, `shared.template.tsx`, `Deck.template.tsx`) and the render script in [`scripts/`](scripts/) encode the same specs as copy-ready files.

## Writing standard

Write the card copy the way a specific, opinionated human editor would explain it — natural Chinese (or the target language), command names and file names in English. [`references/pitfalls.md`](references/pitfalls.md) pitfall 2 lists the coined terms the first translationese draft produced, and the natural-language rewrites that replaced them.
