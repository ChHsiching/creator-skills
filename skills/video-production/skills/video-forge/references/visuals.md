# Visual craft

Companion depth to delivery.md's G1 preflight — read both at G1. Sections here split two ways: construction-time craft — type, symbols, line-width, band, animation timing, card copy, icons and numbers, screenshot placement, component pitfalls — rides the director brief at handoff; stills discipline and design taste serve the review loop.

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

## Animation timing

- A group of labels or chips enters one per beat, in the order the narration names them — never the whole group at once.
- The page's subject is the first thing that moves. An opening that animates only the header's small type for several beats reads as broken; a hero element enters centered and ascends to its resting place early, not late.
- Entering elements make room: new content pushes existing content aside instead of overlapping it.
- Late-arriving content gets dwell time — an element appearing near a page's end is never cut on the following beat. Anything meant to be read (a command) stays visible for at least its spoken duration; genuinely short-lived material enters earlier or gets its own page.
- A page thinned by a re-split fails density: merge the content back into one page (upper half fades out as the lower rises) instead of shipping a sparse page — and re-check that the page's title still states its content plainly, not a stunt phrase.

## Icons, logos, GIFs

- Icons map 1:1 to item semantics (storage → database, search → magnifier); the same icon repeated as decoration in one list is filler; a section header already carrying a mark leaves item-level icons empty. Small graphics ride the line they belong to (a flex slot), never their own row.
- A project with no official logo gets no logo — an author avatar is not one. Square logos display plain, without rounded containers. Dark logos on light backgrounds (mean brightness < 80) get brightened and saturated first.
- README demo GIFs embed directly: `@remotion/gif` (same version as Remotion core), `loop={false}`, explicit width/height, phase long enough for the GIF to play out before the cut. A curl'd "png" may actually be a GIF — verify with PIL before use; and the GIF's first frame makes a misleading still — never reuse it as one.

## Numbers on screen

One data file is the single exit for on-screen numbers; components never inline them. Formatting uses tiered floor truncation (kfmt-style), never `toFixed`. Fast-moving numbers (stars, downloads) carry as-of dates (rule: materials.md), and every data line names its platform ("HuggingFace 获赞 437" — never a bare "获赞 437"). Wording quoted from official material stays verbatim — abbreviating it ("西藏自驾游 PPT" → "定制游 PPT") is a rejection. OCR/vision-read numbers are UNVERIFIED until re-checked against a text source (materials.md). Roundup/recommendation closing cards carry each item's install command verbatim from its official README — never composed or shortened — plus its stars.

## Card copy (designed screen text — cards, terminals, headlines)

- Prose copy carries zero parentheses (syntax inside commands and code is exempt). A parenthetical becomes a · separator or a designed side label; the label of record for bare version numbers and recurring jargon is an **anchor tag** — a small marker beside the token stating what it is (rc.1 — 最新版; 0.17.1 — 上一稳定版; runtime 0.1.0 — 08-14 首发). Without anchors, viewers who don't track version numbers read a ledger. The tag never repeats what the adjacent text already says, and its visual style is free (hairline + small mono worked once; anything equivalent reads fine).
- Every sentence keeps its subject. A compound sentence that drops its subjects reads as a riddle — split it into short sentences, each saying who does what. Flow diagrams carry a subject per step (who does what where → what it hands to whom → where it lands); "its interface? it who?" is the sound of this failing.
- Screen text is not the frozen subtitle: after audio and subtitles freeze, card text that never entered the audio track can still be rewritten for clarity.
- A terminal's side note states real information — how the command actually arrives ("随桌面版一起安装 · 官网下载") — never "一条命令配好" filler; when one is found, sweep the same class film-wide after presenting every instance, the fix scope, and the plan for the user's yes.
- Visible text is plain text: backticks and markdown markers render literally.
- Big-type titles use plain nouns. A spoken antithetical slogan that barely passed the ear becomes several times worse blown up as a screen headline — spoken lines are never reused as card headlines.

## Screenshots and images

- Vision-read every candidate image before placement: what it actually shows, whether it stays legible at target size, and whether it matches the caption. Images that don't fit get their own page or phase — never squeezed to stamp size beside a list.
- Screenshots of a repository are that repository's own original images — never externally downloaded substitutes, never the author's pre-cropped fragments (one cropped fragment cut characters in half; the project's docs carried the full-window capture that replaced it).
- Within the space it gets, an image runs as large as it fits — display share is enlarged before it is shrunk (this is layout size, distinct from the resolution upscale below; one production enlarged seven placements rather than letterbox them).
- No decorative matting: a border added to make edges look less clipped was rejected on sight — the original thin frame and shadow stay.
- A defect the source image itself carries (a half-character at its edge) is fixed by scanning columns for a clean boundary and tightening the crop — not by shipping the defect.
- Source narrower than 2× the display width gets upscaled first (LANCZOS ×2 + unsharp, radius=2, percent=90).
- Capture and placement mechanics are in materials.md's Screenshot capture; local assets load through `staticFile()` (http URLs excepted).

## Stills discipline

- Every scene renders entry + settled frames; both re-render after any scene-code change — mtime-compare `src/scenes/` against `out/stills/` catches stale sheets (one production shipped 13-minute-old entry frames).
- Stills can't catch animation-order bugs — G1's two-frame self-check (delivery.md) is the minimum.
- Occasional 30s still-render timeouts clear on retry; a burst of failures is usually the Google Fonts CDN being flaky — wait it out, don't rewrite code.
- A vision pass is void after fixes — the fix itself introduces defects; changed scenes get re-reviewed.
- Re-exporting stills deletes the previous sheet by explicit list first (never a wildcard; a contact-sheet build excludes its own output from its glob).
- Vision false positives get triaged, not fixed: gap-period fades and mid-fade dim subtitles are normal. Measurable things (frame diffs, band coverage, text zones) are computed with PIL; vision models assist.

## Design taste

AI-template shapes are rejected: saturated fill blocks, rounded-rectangle stacks, left color bars, black boxes around content. Editorial restraint instead: top rules, hairline dividers, tints — frame chrome outshining content is the failure. When the user rejects a visual element: render 2-4 concrete variants for them to pick; arguing attribution or proposing a single guessed alternative both lose. Pre-screen rendered variants with a vision read before presenting (the user still final-judges).

## Component pitfalls (measured)

- A scene shell's content area needs `display: flex; flex-direction: column` — under a block container, children's `justifyContent: center` is dead code and sparse pages stack at the top with a void below.
- Terminal/command blocks size to `fit-content` — a fixed width either clips the nowrap command or leaves a void beside it.
- A `<Sequence>` defaults to `layout="absolute-fill"`: it wraps children in a full-frame absolutely-positioned box that escapes the outer layout — an embedded video placed this way covered the labels and notes beside it. Nesting media takes an explicit `layout="none"`, which leaves the Sequence timing-only and the child in the layout flow.
- `OffthreadVideo`'s playhead follows the composition's clock, not the phase it sits in — a video meant to play from its own start inside a phase gets wrapped in its own `<Sequence>` to zero the clock, or it joins mid-play.
