# Card anatomy — the framework, not a template

The framework below is fixed because the audits and the export depend on it. Everything else — layout, composition, decorative language, type pairing — is **designed fresh for each deck** from the theme's character and the material. `assets/` contains samples from finished decks for inspiration; they are reference, never starting points. A deck that looks like the previous deck is a defect.

## The fixed framework

### Canvas contract

```
width: 1080px, height: 1440px    // 3:4. Export = PNG size at 3x.
overflow: hidden
borderRadius: 0                  // rounded container corners export transparent
data-card={index}                // render + audit anchor
```

Content area: absolute inset 0, `padding: 150px top / 118px bottom / 72px x` (≈1172px usable height). Footer strip sits at bottom ~38px; the 118px clearance keeps content off it.

### Anchors the audits rely on

- Shell root: `data-card={index}`
- Takeaway/final block: `data-takeaway="true"`
- Footer: `data-footer="true"`
- Pure decoration that overflows the canvas: `data-decor="true"` (excluded from layout checks)

Detection is by these attributes on every theme — never by hunting a theme's accent RGB.

### Typography floors (thumbnail legibility)

Feed thumbnails are ~300px wide. Floors, minimums not targets:

| Role | Size | Weight |
|---|---|---|
| Card title | 72px (58px dense cards) | 700 |
| Lead under title | 30px | 600 |
| Body | 28px | 400 |
| Rows/labels | 26px | 700 label / 400 body |
| Takeaway | 28px | 700 |
| Footer | 24px | 600 |
| Secondary annotation | 20px floor | — |

Weights cap at the webfont's range. Line-break rules live in [`typography.md`](typography.md) — the floors and the breaks are one discipline.

### Icons

SVG line icons, `stroke=currentColor`, 24×24 viewBox, round caps. Emoji never renders consistently across systems and fights the palette. A small hand-authored set (check / x / arrow / bulb / terminal / …) beats an icon library for coherence.

## Screenshots in cards

The screenshot's aspect ratio belongs to its content. Fit the **layout to the screenshot** — move and resize it, never stretch/crop it to fit a pre-designed container.

- Crop at element boundaries of the source page (find sections via `getBoundingClientRect`); a mid-element cut is a defect.
- Budget before embedding: usable height ≈1172px minus title/footer furniture; image height = display width × source aspect. If it doesn't fit legibly, the screenshot gets its own page with the furniture dropped — a screenshot page holds title + framed screenshot, nothing else.
- Embed via `import img from "../assets/x.png"` — string `src` paths silently 404 after the single-file build.
- Shoot at deviceScaleFactor ≥ 3× the display scale so 3x export stays sharp.

## Visual approaches (inspiration, not inventory)

Each card earns one visual idea that carries its point. Repertoire seen to work — reach for these shapes when they serve, invent when they don't: split-screen cover (accent block + canvas block) · layered concept cards · flow steps with numbered nodes · before/after compare panels · mapping rows (`from → to`) · big anchor text (a command/name at 80–200px) · stat pills · terminal mocks · full-bleed evidence pages.

## Filling the canvas

Density fills; spacing fakes. A void (content in the top half, empty bottom) is fixed by adding a visual block or restructuring distribution — enlarging gaps produces a scattered card with no center of gravity. The reverse failure, overflow past the footer, is fixed by compressing real content, keeping the plan's must-keeps. Both are caught by `scripts/verify.mjs`.
