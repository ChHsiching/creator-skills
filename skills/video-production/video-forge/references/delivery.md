# Delivery playbook

Render strategy, covers, platform variants, publish copy. These are defaults — do them, and mention them, rather than asking.

## Check render → final render

Always render a cheap check version first and have the user confirm content:

- 540p (scale 0.5) renders ~2× faster than 1080p in practice — per-frame overhead dominates at small sizes, so the 4× pixel ratio does not translate 1:1. (360p via scale is not an option: a decimal third (0.3333×1080 = 359.964) lands on a fractional height and the renderer rejects non-integer dimensions — stick to 0.5/0.75, or build an actual 360p composition.)
- Only after the user confirms content: final render. At 4K, `remotion-4k-polish` owns the path choice — read it before rendering.

## Long-video render strategy (anything over ~15 minutes)

**Maximize parallelism to the actual hardware — measure, then compute, never accept a default queue count:**

1. Probe: logical CPU count and FREE RAM (not total — a "cleaned" machine frees twice the queues).
2. Calibrate on the first render: an instance saturates ~3-4 cores regardless of `--concurrency` (architectural), but its RAM scales with output resolution (~6-8GB at 4K, less at 1080p) — measure one running instance, then compute `queues = min(floor(cores/4), floor(free_ram_gb / measured_instance_gb), remaining_segment_count)`. Two remaining segments means two queues; a third lane has nothing to render.

- **Segmented rendering**: split into N frame-exact segments (each an independent encode), render sequentially or in 2-3 parallel instance queues, concat with stream copy. Zero quality loss: same encoder settings per segment, no re-encode at the join.
- **Resume**: segments already on disk are skipped — a crashed run costs only the in-flight segment.
- `render_segments.sh` gates concat on the integrity check itself; a hand-driven segment run needs `scripts/check_segments.sh` first.

## Ending & completion rate

- Endings stay tight: the video ends when the music ends — fade the audio out over the outro and cut. Silent tails cost completion rate.
- Outro sequence budget: single-digit seconds per card; a sign-off card needs ~3-4s total, never 15.
- Platform variant cards (e.g. bilibili triple-action) render as a **composition props variant** inserted before the outro — the variant is part of the timeline with native transitions. File-level concat of a separately rendered tail produces sample-rate mismatches and hard cuts; a props variant makes both versions from one codebase.

## Covers

- One cover per ratio the intake platform list implies — typically 16:9 (1920×1080) and 4:3 (1440×1080) for bilibili/xiaohongshu; a YouTube-only job needs no 4:3. **A 4:3 cover is its own layout** — vertical space runs out differently, so design it from scratch (move footnotes, re-center blocks, re-fit type); scaling a 16:9 layout down produces wrapped titles and clipped cards.
- Large type only — everything a thumbnail must communicate at ≥48px at 1080-scale. Small text on covers is invisible in feeds; write nothing you wouldn't read at 200px wide.
- Chinese title should be sans/bold (serif CJK reads thin at cover sizes) and at least as prominent as any English title — viewers read the language they know to decide what the video is.
- **Verify by reading, not by metric**: downsampled-pixel brightness checks are blind to thin/colored text (green prompt lines, gray footnotes — all below threshold). Downscale the full cover to ASCII art and read it; this catches wraps, overlaps, and missing elements that metrics pass.
- The cover is an independent design — a frame from the video is not a cover.

## Publish copy

Per-platform deliverable, written after the video is final (facts on screen are then frozen):

- **Titles**: per platform, length verified against the live limits (historically bilibili 80, xiaohongshu ~20 — verify, never assume the shorter). A title tells the viewer what happens in the video, not a slogan.
- **Description** (long platforms): five-part structure in order — positioning line (who did what, one sentence of value), numbered hooks (why watch, with suspense), key-content list (· bullets, label: content), source block (author/original URL/related links), closing note (subtitle credit line).
- **Chapters**: platform field versions respect their current limits (historically bilibili ≤10, xiaohongshu ≤15) with short names, plus one full descriptive list for a pinned comment.
- Plain text only inside paste blocks — platforms render markdown literally; bullets use `·`, never `-`.
- Verify counts with `len()` against each platform's counting rule before handing over.
- **Character-capped platforms**: where the description field can't hold the five-part structure, deliver a short body plus a pinned-comment variant (≤300 chars by that platform's own counting) carrying the source links and the subtitle credit line.
