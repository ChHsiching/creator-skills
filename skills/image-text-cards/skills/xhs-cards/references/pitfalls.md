# Pitfalls — eight verified failure modes

Each pitfall here was hit and fixed in production (the mattpocock/skills v1.2 deck). They are written as the concrete fix the run verified, with the real symptom that surfaced — so the next run applies the fix, not a re-invention. Read this file before Step 5 (building cards) and again before Step 7 (layout verification).

## Pitfall 1 — Emoji as icons

**Symptom**: the user said "太丑了" (too ugly). Emoji renders inconsistently across OSes and clashes with the theme palette.

**Fix (verified)**: an Icon component — hand-authored SVG line icons, `stroke=currentColor`, 24×24 viewBox, round line caps. The Takeaway `icon` prop takes a string name (`plug`, `target`, …), never an emoji character. See [`card-anatomy.md`](card-anatomy.md) "Icon" for the component spec and the verified icon set.

**Check**: grep the card files for emoji ranges; the set should be empty.

## Pitfall 2 — Translationese and coined terms

**Symptom**: the user said "翻译的措辞很奇怪，各种自造词，不像正常人说话" (weird phrasing, coined terms, doesn't sound like a normal person).

This happens when the source is English and you translate word-by-word instead of rewriting in natural Chinese. The first draft of the source produced these — none of them are words a Chinese developer would actually say:

> 重新 pitch · ubiquitous language · 啃字 (clip words) · 听者状态 (listener's state) · 机制即名字 (the mechanism is the name) · 一手来源 (primary source) · AFK · frontier · charting · over-reaching

**Fix (verified)**: rewrite the source in natural Chinese first (`source/source.<lang>.md`), then write the cards from that. Keep these in English: command names (`/wait-what`), file names (`SKILL.md`), config keys (`allow_implicit_invocation`), product names (`Claude Code`). Rewrite everything else the way you would explain it to a colleague.

**Test**: read each line aloud and ask "would a Chinese developer actually say this?" If it sounds translated, rewrite it.

## Pitfall 3 — Font sizes too small

**Symptom**: the user said "字还是有点小" (the text is still a bit small). Xiaohongshu feed thumbnails are ~300px wide; small fonts become illegible at that scale.

**Fix (verified)**: the font-size floor in [`card-anatomy.md`](card-anatomy.md) "shared typography". Title 72, body 28, SoftRow 26, Takeaway 28. Secondary annotations down to 18-20px; primary information stays at the floor.

## Pitfall 4 — Rounded container corners

**Symptom**: the exported PNGs had transparent rounded corners ("截图的角落是圆角啊").

**Root cause**: the Card shell had `borderRadius`, and Playwright's element screenshot captures the rounded shape — leaving transparent pixels at the four corners.

**Fix (verified)**: `borderRadius: 0` on the Card shell. Visual roundness lives inside the card (pills, blocks); the container stays square.

**Check**: after export, read each PNG with PIL and verify all four corner alphas are 255. See [`export.md`](export.md) "corner verification".

## Pitfall 5 — Content overlapping the footer (overflow direction)

**Symptom**: the user said "12页内容溢出和页脚重叠了" (page 12 overflows and overlaps the footer).

**Root cause**: the footer is `position: absolute; bottom: 0`. When a card's content is dense, the Takeaway (which uses `marginTop: auto` in a flex column) gets pushed below the content area's bottom padding and lands on top of the footer.

**Fix (verified)**:
- Content area `paddingBottom: 104px` (gives the ~60px footer room + ~40px gap).
- After building all cards, measure every card: Takeaway bottom vs footer top, gap must be > 0. See [`export.md`](export.md) "layout measurement".
- When a card overflows, compress the layout (verified techniques): vertical list → horizontal pills; shrink gap (12→8) and padding (20→16); merge items (3 rows → 2). Cut redundancy and decorative spacing; keep the information the plan marked must-keep.

**Real data from the run**: cards 12 and 14 overlapped by 8px each. Card 12 was fixed by turning a 5-row vertical decision tree into 5 horizontal pills + dropping prototype rows 3→2 + gap 12→8. Card 14 was fixed by shrinking the byline block padding 22→16 and font 26→24. After fix: gaps were 27 and 12 respectively.

## Pitfall 6 — Output scattered into the parent directory

**Symptom**: screenshots and PNGs landed in the parent workspace, polluting it.

**Fix (verified)**: every output goes into a subdirectory of the card workspace — `preview/` for 1x check screenshots, `exports/` for 3x delivery PNGs. Playwright's screenshot path is relative to its own cwd; pass a path that resolves inside the card workspace.

## Pitfall 7 — Caption character limits exceeded

**Symptom**: the user said "100字早超了啊" (it's way over 100 characters). The first caption draft had multi-paragraph bodies far exceeding the limit.

**Fix (verified)**: the limits in [`caption-spec.md`](caption-spec.md). Title ≤20, body ≤100, pinned comment ≤300 (every character including spaces and punctuation — that is how the platform counts). Write, then verify with `len()`; if over, compress. No marketing tone ("大佬带你", "效率翻倍").

## Pitfall 8 — Visual weight imbalance (the core quality standard)

**Symptom**: cards that look "broken" — either content piled in the top half with the Takeaway stranded at the bottom leaving a void, or elements forced apart with large gaps to fake fullness.

This is the failure mode other agents reach for most often, because the instinctive fix — "there's empty space, push things apart" — makes it worse.

**Two failure modes**:
- **Void**: content occupies only the top half. Takeaway, using `marginTop: auto`, sits at the very bottom. The middle is empty. From a distance the card looks like half an image.
- **Forced gap**: to "fill" the void, gaps between elements are enlarged. The content scatters. There is no center of gravity.

**Fix — fill the canvas by density.** Enlarging gaps to fill space produces the second failure mode (scattered, no center of gravity); add visual blocks or restructure instead. Verified techniques from the run:

| Situation | Verified fix |
|---|---|
| Content too sparse (void) | **Add a visual block** — a diagram, a compare panel, an expanded list, a stat pill. Or **restructure the distribution** — the cover's first draft was "big circle top-left + centered text"; it was rebuilt as a split-screen (upper accent block 42% holding the version number, lower canvas 58% holding title + lead + three stat pills + byline). Both halves now hold real content. |
| A point that is one line of text | **Expand it into a visual block** — the overview page turned "platform layer 3 items + skill layer 4 items" into two LayerCards (title + description + item rows), not paragraphs. Item rows are themselves visual blocks. |
| A command name or key number | **Enlarge it into a visual anchor** — `/wait-what` at 80px with a "啰嗦 →" state visual; the 3/1/6 counts became three large stat pills. Large typography fills canvas by itself. |
| Content too dense (overflow, the opposite extreme) | See pitfall 5 — compress layout; keep must-keep information. |

**The single rule**: fixing a void means adding content or restructuring distribution. Enlarging gaps produces the scatter failure mode instead.

**Check**: screenshot the card, hide the Takeaway mentally — if the top half looks empty, the card has a void. Add a visual block or restructure; then re-screenshot. See [`export.md`](export.md) "layout measurement" for the DOM-assisted check.
