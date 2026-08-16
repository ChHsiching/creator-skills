# Card anatomy

The card layer this skill adds on top of beautiful-article's scaffold. Every spec here is verified in production (the mattpocock/skills v1.2 deck, andy theme, 14 cards). Apply it as-is.

## Workspace reshape

beautiful-article's scaffold produces a flowing article (`Article.tsx` + `Cover.tsx` + `sections/`). Delete those three, then build the deck:

- `article/main.tsx` — `<ThemeProvider theme="<id>">` wrapping `<Deck/>`. No `<Article>`.
- `article/Deck.tsx` — assembler. Imports and orders the N card components. One card per file under `article/cards/NN-*.tsx`.
- `article/Card.tsx` — the shared shell (below).
- `article/cards/_shared.tsx` — shared typography + Icon (below).
- `article/cards/01-cover.tsx` … `NN-ending.tsx` — one file per card.

## Card.tsx — the shared shell

The shell holds the fixed canvas, the page badge, the category tag, the footer, and a decorative dot. Card content goes in `children`.

```
width: 1080px, height: 1440px    // 3:4. Export size = PNG size.
overflow: hidden
borderRadius: 0                   // PNG must be square. Rounded corners leave transparent corners.
data-card={index}                 // screenshot anchor
```

- **Header** (hidden on cover): page badge (theme-accent filled circle, e.g. andy's pumpkin `--hs-orange`) + category tag (soft-accent pill).
- **Content area**: `position: absolute; inset: 0; paddingTop: 120px; paddingBottom: 104px; paddingX: 72px`. The 104px bottom clearance gives the footer (~60px) room plus a ~40px gap — without it, a full card's Takeaway overlaps the footer.
- **Footer** (hidden on cover): brand line + `index / N` page count.
- **Cover variant** (`variant="cover"`): hide header + footer, zero the content padding — the cover fills the whole canvas itself.
- **Decorative dot**: a large low-opacity theme-accent circle at the bottom-right corner (`bottom: -60px`), the andy "imperfect circle" motif. It intentionally overflows the container (clipped by `overflow: hidden`); exclude it from layout-overflow checks.

## _shared.tsx — shared typography

Font sizes are large because Xiaohongshu feed thumbnails are ~300px wide — small text becomes illegible. These are the floor, not a suggestion:

| Component | Size | Weight | Notes |
|---|---|---|---|
| CardTitle | 72px | 800 | Main title of each card |
| CardTitleSm | 58px | 800 | Dense cards |
| CardLead | 30px | 600 | One-line framing under the title |
| Body | 28px | 400 | Prose paragraphs |
| SoftRow | 26px | 700/400 | Label (accent) + body (text); list items |
| Takeaway | 28px | 700 | Bottom one-liner, accent-fill background |
| Icon (in Takeaway) | 34px | — | SVG line icon |
| Footer | 24px | 600 | Brand + page count |

Colors use only `--ra-*` tokens and the theme's accent tokens (e.g. andy: `--hs-orange` for fills, `--ra-color-accent-strong` for text-carrying accent). Bright accent fills; deepened accent for text legibility.

## Icon — SVG, never emoji

Emoji renders inconsistently across systems and clashes with the theme palette. The Icon component is a set of hand-authored SVG line icons (Feather-like: `stroke=currentColor`, 24×24 viewBox, round caps). The Takeaway's `icon` prop takes an icon **name** (a string key).

Verified icon set: `plug`, `puzzle`, `book`, `edit`, `target`, `wand`, `clipboard`, `tree`, `folder`, `compass`, `broom`, `bulb`, `check`, `x`. Add more by appending to the `ICON_PATHS` map — each entry is JSX of `<path>` elements.

For status pairs (yes/no, do/don't), use `check` and `x` with semantic colors: `check` in `--ra-color-success`, `x` in `--ra-color-risk`.

## Visual techniques (verified repertoire)

Every card earns a visual technique that serves its core idea. These are the ones verified in production — reach for them before inventing new ones:

| Technique | When | Example |
|---|---|---|
| **Split-screen cover** | Cover card | Upper accent block (42%, holds version number + eyebrow) / lower canvas block (58%, holds title + lead + stat pills + byline) |
| **Layer cards** | Overview / multi-item | Two stacked tinted cards (platform layer / skill layer), each with label + description + item rows |
| **Flow steps** | Process / pipeline | N steps as columns: numbered circle + title + caption, arrows between |
| **Compare panels** | Before/after, old/new | Left vs right tinted panels with strikethrough old → highlighted new |
| **Mapping rows** | Merges / redirects | `from → to` per row, with a "because" note underneath |
| **Big anchor text** | Skill name / key concept | The command name at 80px as the visual focus, with a state arrow (啰嗦 → /wait-what) |
| **Stat pills** | Counts / numbers | Large number + small label, in a tinted rounded card |
| **Process chain** | Main flow | Vertical or horizontal numbered chain (① → ② → ③) in a tinted panel |
| **Terminal mock** | CLI / interactive | A mock terminal panel showing steps, hidden input, progress |
| **Role flow** | Handoff / routing | Role boxes connected by arrows (you → questionnaire → them → answer) |
| **Decision tree** | Options / router | Horizontal pills (numbered, ordered) in a tinted panel |
| **Config card** | Code / config | Monospace block on a surface panel, syntax-colored with theme tokens |

## Theme accent color (for layout detectors)

The overflow detector (Step 7) finds the Takeaway by its theme-accent background color. The RGB value differs per theme — read it from `node_modules/reacticle/src/theme/themes/<id>/<id>.css` (the `--hs-orange` or equivalent accent-fill variable). For andy: `#ff7e1d` = `rgb(255, 126, 29)`.
