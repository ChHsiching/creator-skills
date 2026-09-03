# Visual craft

Companion depth to delivery.md's G1 preflight — read both at G1. The type floors, band design, line-width math, and component pitfalls here are construction-time rules: they ride the director brief at handoff, not just the review.

## Type and layout

- Type floors for phone-thumbnail viewing: body ≥24px (ideal 29-34); mono labels ≥20px; footnotes 24px. Hero and title sizes are per design system — the floors hold everywhere.
- Hairlines ≥2px at `--scale=2` — 1px hairlines dissolve at 4K (the doubling rule lives in remotion-4k-polish Path C).
- Big numbers set `lineHeight: 1`; timeline cards alternate above/below the axis to avoid overlap.
- Fitting text, in order: explicit line breaks → two columns → tighter spacing; content cuts are the last resort. Shrinking font size to fit is banned; it breaks the floor.
- JSX attribute strings render `\uXXXX` escapes literally — write the actual characters.

## Symbols are SVG

A character performing a graphic role — arrows (→ ←), trend marks (▲ ▼), bullets (● ■), stars (★), vertical dividers (丨) — is an SVG component, never a text glyph: glyph weight varies by font, alignment is uncontrollable, and 4K scaling is lossy. Characters stay characters where they are syntax: math operators, in-sentence punctuation (the · in "A · B"), code. The test: lift the character out of the text flow — when it performs a graphic function alone (pointing, separating, marking), it must be SVG. After any icon swap, verify alignment pixel-wise (the color-cluster method is in delivery.md's G1 preflight).

## Line-width math

Before adding or changing text in a fixed-width container, compute each line's rendered width and break it explicitly at semantic points (after commas, around ·). Auto-wrap is banned as the mechanism — it breaks at arbitrary characters, producing orphan single-character lines and punctuation at line starts (both rejected on real sheets). After any text change, re-export the stills and re-run the read — a passing `tsc` is not a visual check.

## Subtitle band

Route by pipeline: transcribed AV material burns ASS (cook pipeline); original-narration videos render the band in-picture. Two proven schemes; in both, the band's usable width stays decoupled from content padding (`band width = column − 2 × marginX`; one production bound marginX to the content padding and silently lost 170px to wraps — diagnose in Remotion studio by reading the band div's `clientWidth`):

- **Rendered-in-picture band**: bottom whitespace reserved by layout (~70px; the machine-sweep target is zero stray ink in that zone), constructive zero overlap with content, hairline separator fading out at both ends, dark ~30px centered single-line text, no stroke/shadow, hard cue cuts. The band shares the background color — a black bar on a light frame is rejected.
- **Burned ASS band** (cook pipeline): 220px bottom band, content never enters it; machine-sweep the band's 12% side margins for dark pixels, plus edge-clipping scans on the frame.

## Icons, logos, GIFs

- Icons map 1:1 to item semantics (storage → database, search → magnifier); the same icon repeated as decoration in one list is filler; a section header already carrying a mark leaves item-level icons empty. Small graphics ride the line they belong to (a flex slot), never their own row.
- A project with no official logo gets no logo — an author avatar is not one. Square logos display plain, without rounded containers. Dark logos on light backgrounds (mean brightness < 80) get brightened and saturated first.
- README demo GIFs embed directly: `@remotion/gif` (same version as Remotion core), `loop={false}`, explicit width/height, phase long enough for the GIF to play out before the cut. A curl'd "png" may actually be a GIF — verify with PIL before use; and the GIF's first frame makes a misleading still — never reuse it as one.

## Numbers on screen

One data file is the single exit for on-screen numbers; components never inline them. Formatting uses tiered floor truncation (kfmt-style), never `toFixed`. Fast-moving numbers (stars, downloads) carry as-of dates (rule: materials.md), and every data line names its platform ("HuggingFace 获赞 437" — never a bare "获赞 437"). Wording quoted from official material stays verbatim — abbreviating it ("西藏自驾游 PPT" → "定制游 PPT") is a rejection. OCR/vision-read numbers are UNVERIFIED until re-checked against a text source (materials.md). Roundup/recommendation closing cards carry each item's install command verbatim from its official README — never composed or shortened — plus its stars.

## Screenshots and images

- Vision-read every candidate image before placement: what it actually shows, whether it stays legible at target size, and whether it matches the caption. Images that don't fit get their own page or phase — never squeezed to stamp size beside a list.
- Source narrower than 2× the display width gets upscaled first (LANCZOS ×2 + unsharp, radius=2, percent=90).
- Capture mechanics (viewport zoom not CSS zoom, scrollbar crop, natural aspect, objectFit policy) are in materials.md's Screenshot capture; local assets load through `staticFile()` (http URLs excepted).

## Stills discipline

- Every scene renders entry + settled frames; both re-render after any scene-code change — mtime-compare `src/scenes/` against `out/stills/` catches stale sheets (one production shipped 13-minute-old entry frames).
- Stills can't catch animation-order bugs — G1's two-frame self-check is the minimum; spot-check mid-animation frames before presenting the sheet.
- Occasional 30s still-render timeouts clear on retry; a burst of failures is usually the Google Fonts CDN being flaky — wait it out, don't rewrite code.
- A vision pass is void after fixes — the fix itself introduces defects; changed scenes get re-reviewed.
- Re-exporting stills deletes the previous sheet by explicit list first (never a wildcard; a contact-sheet build excludes its own output from its glob).
- Vision false positives get triaged, not fixed: gap-period fades and mid-fade dim subtitles are normal. Measurable things (frame diffs, band coverage, text zones) are computed with PIL; vision models assist.

## Design taste

AI-template shapes are rejected: saturated fill blocks, rounded-rectangle stacks, left color bars, black boxes around content. Editorial restraint instead: top rules, hairline dividers, tints — frame chrome outshining content is the failure. When the user rejects a visual element: render 2-4 concrete variants for them to pick; arguing attribution or proposing a single guessed alternative both lose. Pre-screen rendered variants with a vision read before presenting (the user still final-judges).

## Component pitfalls (measured)

- A scene shell's content area needs `display: flex; flex-direction: column` — under a block container, children's `justifyContent: center` is dead code and sparse pages stack at the top with a void below.
- Terminal/command blocks size to `fit-content` — a fixed width either clips the nowrap command or leaves a void beside it.
