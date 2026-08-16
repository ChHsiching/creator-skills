---
name: paged-article
description: "Paged-article: 3:4 vertical Xiaohongshu pages (one chapter per page, rendered at 3x DPI) from any link, file, or pasted text. Use when the user wants to make 小红书图文/分页文章/竖屏图文笔记, mentions paged-article/分页文章, or asks to turn an article/post/video into shareable image pages."
---

This skill is **beautiful-article + pagination**. Everything about how to write, design, theme, and structure the article comes from beautiful-article — unchanged, in full, in [`references/`](references/), [`theme-profiles/`](theme-profiles/), [`scripts/`](scripts/), and [`assets/scaffold-template/`](assets/scaffold-template/). This SKILL.md only adds what beautiful-article doesn't have: **splitting the article into 3:4 pages, one chapter per page, and rendering each to a 3x PNG.**

Read [`SKILL.md.bak`](SKILL.md.bak) (beautiful-article's original SKILL.md) for the full editorial process (Phase 0–8). The steps below reference it by phase number.

## What you produce

1. `NN.png` — the pages: cover + one chapter per page + ending, each 3240×4320 (3x of 1080×1440)
2. `caption.md` — multiple title options (≤20 chars), body options, hashtags, sources
3. `source/source.md` — the normalized source (from beautiful-article Phase 1)
4. `plan/plan.md` — the editorial plan (from beautiful-article Phase 2)
5. `pages/NN.html` — standalone 3:4 HTML per page (the pagination layer's output)
6. `render.mjs` — the 3x Playwright render script

## The pipeline

### Step 1–3 — Run beautiful-article's full editorial process

Do **exactly** what beautiful-article's SKILL.md (`SKILL.md.bak`) says for Phase 0 through Phase 4 Checkpoint 2:

- **Phase 0–1**: Intake + source → `source/source.md` (read [`references/source-to-markdown.md`](references/source-to-markdown.md) for extraction rules). For images the agent can't analyze, ask the user to transcribe visible text before continuing.
- **Phase 2**: Editorial planning → `plan/plan.md` (read [`references/plan-template.md`](references/plan-template.md), [`references/article-types.md`](references/article-types.md), [`references/theme-selection.md`](references/theme-selection.md)).
- **Phase 3 Checkpoint 1**: Confirm article type / theme / width / assets / cover with the user — each decision as an independent question, never bundle.
- **Phase 4**: First Spread — scaffold the workspace (`scripts/scaffold.sh`), write cover + first section, run First Spread Reviewer, hit Checkpoint 2.

**Theme selection** (Phase 3): use beautiful-article's theme system — [`theme-profiles/index.json`](theme-profiles/index.json) + per-theme profiles. The agent recommends themes based on content type, confirms with the user. When rendering pages later, the exact CSS tokens come from the reacticle package (installed by scaffold.sh into `node_modules/reacticle/`). Read [`references/themes.md`](references/themes.md) for the hex values and font stacks before inlining any token into a page's `<style>`.

**Done when** Checkpoint 2 is passed (user accepts the first spread + development mode).

### Step 4 — Full article build, then paginate

After Checkpoint 2, build the complete article per beautiful-article Phase 5 — but **with one structural change**: each Section is sized to fit one 3:4 page (1080×1440 CSS canvas), not a flowing web column.

**Pagination rules** (this skill's core addition):

1. **One chapter per page.** Each `<Section>` from the article becomes one standalone HTML page. Aim for content that fits within 1080×1440 without scrolling; the fit is verified by rendering in Step 5 — if a page overflows, split it into two pages or trim, then re-render.
2. **Page structure** (standalone HTML, not React — the pages are rendered by Playwright, not served by Vite):
   - **Cover page** (`pages/01.html`): the article's Cover design (from beautiful-article's cover system — read [`references/cover.md`](references/cover.md)), adapted to the 1080×1440 canvas. Includes: watermark, SVG hero visual, eyebrow, title, lead, meta row.
   - **Chapter pages** (`pages/02.html` … `pages/NN-1.html`): header (chapter number + name + series) → h2 title → lead → prose paragraphs → SVG diagrams / compare tables / quote blocks / aside callouts (as beautiful-article's [`references/component-policy.md`](references/component-policy.md) and [`references/raw-policy.md`](references/raw-policy.md) dictate) → footer (page number).
   - **Ending page** (`pages/NN.html`): summary + note + END stamp.
3. **Theme tokens inlined**: each page's `<style>` hardcodes the chosen theme's CSS values (from [`references/themes.md`](references/themes.md) or the runtime `node_modules/reacticle/` CSS). Pages load fonts via Google Fonts `<link>`.
4. **SVG diagrams by hand**: when a concept earns a visual, write inline SVG using the theme's tokens (read [`references/raw-policy.md`](references/raw-policy.md) for Raw rules). Default to zero image-API calls — the visuals are hand-authored SVG and typography.

**Convert from React to standalone HTML**: beautiful-article produces `.tsx` (React + reacticle). For pagination, translate each Section's content into plain HTML with the theme's tokens inlined. The structural components map directly:
- `<Section>` → `<div class="body">` with header + footer
- `<Aside>` → `<div class="aside">` with label + body
- `<Quote>` → `<div class="quote">`
- `<Raw>` → inline SVG/HTML
- Prose paragraphs → `<p>` tags

**Done when** every chapter exists as a standalone `pages/NN.html`. (Fit within 1080×1440 is verified in Step 5 by rendering.)

### Step 5 — Render all pages at 3x

```bash
node render.mjs pages/NN.html NN.png
```

The render script uses Playwright with `deviceScaleFactor: 3` — CSS canvas stays 1080×1440, PNG output is 3240×4320. This gives serif strokes enough pixels to render sharply on mobile screens.

Verify each page: no overflow past 1440px, no text/footer overlap, fonts loaded (not fallback), SVG integrity. Fix and re-render until clean.

**Done when** every page is a clean 3x PNG.

### Step 6 — Adjust loop

Show the user the full set. Adjust:
- **Text/layout** (HTML) — free, instant.
- **Theme switch** — re-render with different tokens.

**Done when** the user approves.

### Step 7 — Caption

Write `caption.md`:
- **Multiple titles** (≤20 chars, verified by script, none duplicating the cover text).
- **Multiple body options** (plain text, no markdown).
- **Hashtags.**
- **Sources block** for a pinned comment.

**Done when** caption.md exists with verified titles and body options.

## Writing rules

Follow beautiful-article's writing standards — read [`SKILL.md.bak`](SKILL.md.bak) "成功标准" and [`references/section-build.md`](references/section-build.md), [`references/component-policy.md`](references/component-policy.md). Write the way a specific, opinionated human editor would: vary sentence openers, concrete verbs over abstract nouns, full paragraphs with transitions, structural callouts (aside/quote/compare) for emphasis rather than inline bolding, and SVG diagrams only when a concept is faster shown than told.

## File map

```
paged-article-skill/
├── SKILL.md                  ← this file (orchestration + pagination layer)
├── SKILL.md.bak              ← beautiful-article's original SKILL.md (Phase 0–8 reference)
├── render.mjs                ← 3x Playwright render script
├── references/
│   ├── themes.md             ← runtime CSS token lookup (hex + fonts per theme)
│   ├── cover.md              ← cover design system (from beautiful-article)
│   ├── component-policy.md   ← reacticle component protocol
│   ├── raw-policy.md         ← Raw layer rules
│   ├── ... (all beautiful-article references)
│   └── article-types/        ← per-genre authoring guides
├── theme-profiles/           ← 11 theme authoring profiles + index.json
├── scripts/                  ← scaffold.sh, html-to-pdf.sh, source-to-markdown scripts
└── assets/scaffold-template/ ← Vite+React+TS workspace template
```
