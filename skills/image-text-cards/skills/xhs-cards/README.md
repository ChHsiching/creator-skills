# xhs-cards

A skill that turns any link, file, or pasted text into a set of 3:4 Xiaohongshu (小红书) image cards — a cover, one idea per page, an ending — each rendered to a 3x PNG (3240×4320).

It is a **router**: it orchestrates [`beautiful-article`](../beautiful-article/SKILL.md) for the content work (source extraction, editorial planning, theme system, scaffold) and adds the three things beautiful-article does not do:

1. **Reshape the article into a card deck** — N standalone 3:4 cards (1080×1440 CSS canvas), one idea per card, not a flowing web article.
2. **Render each card to a 3x PNG** — via Playwright at `deviceScaleFactor: 3`.
3. **Write the caption** — Xiaohongshu titles, body, pinned comment, chapter list, with character limits verified by `len()`.

## Install

```bash
npx skills add ChHsiching/xhs-cards-skill
```

It requires `beautiful-article` to be installed alongside it (it delegates Phases 0–3 and the scaffold to that skill).

## What's in here

```
xhs-cards-skill/
├── SKILL.md                  ← the pipeline (10 steps) + leading words
├── references/
│   ├── card-anatomy.md       ← Card shell spec, shared typography, Icon system, visual techniques
│   ├── pitfalls.md           ← 8 verified failure modes + the concrete fixes
│   ├── export.md             ← 3x render script, corner verification, layout measurement
│   └── caption-spec.md       ← caption structure, character limits, verification
├── assets/
│   ├── Card.template.tsx     ← Card shell (square corners, footer clearance, cover variant)
│   ├── shared.template.tsx   ← shared typography (Icon component, large font sizes)
│   └── Deck.template.tsx     ← Deck assembler
└── scripts/
    └── export-png.mjs        ← 3x render script
```

## How it was written

This skill was distilled from a production run (the mattpocock/skills v1.2 changelog → 14-card andy-theme deck). Every pitfall in `references/pitfalls.md` was hit and fixed during that run — the fixes are the ones the run verified, not invented after the fact. The card anatomy, font sizes, Icon system, and visual techniques are all taken directly from the deck that shipped.
