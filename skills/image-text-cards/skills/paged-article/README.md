# paged-article — Beautiful-article-style essay as 3:4 swipeable pages

> Turn any source (URL / file / pasted text / image) into a set of **3:4 vertical pages** for Xiaohongshu — a prose-first essay, split one-chapter-per-page, each rendered as standalone HTML at 3x DPI.

---

## What it does

Give it a link, a local file, pasted text, or an image. It produces:

- **3:4 pages** (3240×4320 PNG at 3x) — cover + one chapter per page + ending
- **caption.md** — multiple title/body/hashtag options for posting
- **source.md** — the normalized source + translation notes
- **pages/*.html** — the HTML source for each page (re-renderable)

The prose reads like an edited article. The layout uses a real theme's design tokens. SVG diagrams explain concepts where they earn their place. Zero AI-image cost by default.

## How it works

This skill is **beautiful-article + pagination**. It embeds [beautiful-article](https://github.com/ConardLi/garden-skills) in full — all references, theme-profiles, scripts, and scaffold-template — unchanged. On top of that, it adds:

1. **Pagination**: split the article into 3:4 pages, one chapter per page
2. **3x render**: Playwright screenshots at `deviceScaleFactor: 3` (3240×4320)
3. **Caption**: title/body/hashtag options for Xiaohongshu posting

```
paged-article
    │  embeds
    ▼
beautiful-article  (full editorial process: source → plan → theme → build)
    │  composes
    ▼
reacticle          (npm package: components / themes / Raw / export)
```

| Layer | What it owns |
|---|---|
| `paged-article` (this skill) | Splitting the article into 3:4 pages, 3x rendering, Xiaohongshu caption |
| `beautiful-article` (embedded) | How the agent plans, writes, designs, themes, and reviews the article |
| `reacticle` | The component vocabulary + 11 authoring themes |

## Flow

1. **Acquire** the source (URL/file/text/image) → `source.md`
2. **Plan** the chapters (beautiful-article Phase 0–2, user confirms)
3. **Pick a theme** (render multiple cover thumbnails, user chooses — beautiful-article Phase 3)
4. **Build + paginate** (beautiful-article Phase 4–5, then split into 3:4 pages)
5. **Render** all pages at 3x
6. **Adjust** (free HTML tweaks until the user is happy)
7. **Caption** (titles ≤20 chars, body options, hashtags, sources)

## Install

```bash
npx skills@latest add ChHsiching/paged-article-skill
```

Or clone manually and copy into your skills folder. Requires:
- `playwright` (`npm i playwright`) in the run directory
- `reacticle` (installed automatically by `scripts/scaffold.sh` via `npm install reacticle@latest`)

## File map

```
paged-article-skill/
├── SKILL.md                  ← orchestration layer (beauty full process + pagination)
├── SKILL.md.bak              ← beautiful-article's original SKILL.md (Phase 0–8 reference)
├── render.mjs                ← 3x Playwright render script
├── references/
│   ├── themes.md             ← runtime CSS token lookup (hex + fonts per theme)
│   ├── cover.md              ← cover design system (from beautiful-article)
│   ├── component-policy.md   ← reacticle component protocol
│   ├── raw-policy.md         ← Raw layer rules
│   └── ... (all beautiful-article references + article-types/)
├── theme-profiles/           ← 11 theme authoring profiles + index.json
├── scripts/                  ← scaffold.sh, html-to-pdf.sh, source-to-markdown scripts
└── assets/scaffold-template/ ← Vite+React+TS workspace template
```
