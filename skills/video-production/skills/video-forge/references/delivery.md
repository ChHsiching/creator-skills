# Delivery playbook

Mechanics for the delivery gates, timing, verification, audio, covers, platform variants, and publish copy. These are defaults — do them, and mention them, rather than asking. The gate names and the advance-blocking rule live in SKILL.md Step 5; this file carries each gate's **checks** (a pinned command where the check is mechanical, a defined procedure where it is a user approval or a vision read). Every gate is judged by running its check and reading the result against stated numbers — a downstream "done" or a self-assessed pass never clears a gate; only the check does.

## G1 — stills approval

Render one still per distinct layout/asset state (not per scene), present as a labeled sheet, and get the user's explicit go. The gate clears on the user's approval — record it; silence is not approval, and G2's render command is not issued before it.

**Preflight** — self-check the stills before the sheet reaches the user; every line traces to a real rejection. Deeper visual craft (type floors, SVG symbols, line-width math, subtitle band, icons/numbers, stills discipline, component pitfalls) lives in `references/visuals.md` — read it with this list:

- *Thumbnail read*: inspect at phone-thumbnail scale and grow any type that stops reading there. Full-size inspection overstates legibility — viewers meet the thumbnail first.
- *System vocabulary*: extend the established visual system with its own vocabulary (rules, tints, type). Borrowings from other archetypes — card boxes, badges, panels — are a different language; route them through the storyboard for approval instead of slipping them into stills.
- *Optical center*: a centered hero element sits at ~42-45% frame height; the geometric middle reads low.
- *Explicit line breaks*: hand-set where meaning breaks, never auto-wrap (width math and the mechanism ban: references/visuals.md).
- *Attribution tags*: sources ride as small tags beside the claim (官方口径 / 社区结论 style), stated as speech or deleted; parentheticals and narrator self-talk ("下一屏揭晓", "详见X章") go — the sequence itself navigates. Tags are reserved for genuinely third-party data: officially checkable facts state directly, and tagging them as third-party is a downgrade.
- *Self-evident terms*: a term lifted from source material (a demo's scene name, artifact jargon) carries one phrase of setup; proper nouns use the source's display name, never the slug/ID.
- *SVG icons*: arrows and marks are hand-drawn SVG — glyph stand-ins (→ ↓ ▸ emoji) drag in font-metric surprises. After any icon swap, measure alignment pixel-wise (color-cluster the icon ink against its anchor text's ink; inline-SVG baseline behavior is not what you'd guess). The full symbol principle lives in references/visuals.md.
- *Fill voids with content*: an empty region earns another fact, never wider margins.
- *Machine acceptance, every still*: an edge-clipping scan (all content pixels within frame bounds) catches overflow the eye forgives. Render each still at two frames for self-check — the settled frame, plus one from ~20% into its scene's entry animation — and read the early one: a settled-only pass hides animation-order bugs such as elements already visible at frame 0. The user sheet stays the settled frames.

## G2 — cheap full render with audio

Render the full video at 1080p **with the final audio mix in place** — G3a's loudness check reads the real mix, so a silent or scratch-audio draft makes the whole of G3 meaningless. (1080p rather than 540p because G3b's diff threshold and G3c's vision reads are calibrated at full pixels; 540p halves the diffs and blurs the reads. Use 540p only for long videos where 1080p is too slow — see the scale note below.)

The mix itself is one master audio file (voice + music bed) rendered inside the composition's own `<Audio>` timeline: build it from measured segments (strip per-segment leading silence, place by exact delay), then render picture and sound in the same pass. Splitting audio out into ffmpeg and muxing it back drifts — per-source `<Audio volume>` inside Remotion has been measured not to attenuate, and mp3 priming adds ±100-430 ms per segment, so the more you patch it the further it slides.

Two checks, in order:

1. **Spec check** (machine):
   ```
   ffprobe -v error -select_streams v:0 -show_entries stream=width,height,avg_frame_rate -show_entries format=duration -of default=noprint_wrappers=1 <video>
   ```
   fps and duration match the intake answers and the generated timing table (duration here is a fast proxy — the frame-exact count check runs at G4). Dimensions match THIS render's own target (the 1080p/540p draft), never the intake resolution — the intake-set dimensions are what G4's platform variants check.
2. **User check**: the user watches and approves content and timing.

(540p via scale 0.5 is ~2× faster than 1080p — per-frame overhead dominates. 360p via scale is not an option: a decimal third of 1080 lands on a fractional height and the renderer rejects non-integer dimensions — stick to 0.5/0.75.)

## G3 — content gates on the cheap render

All four run on the G2 file — content truth lives in the rendered file (a stale bundle renders stills fine while the video breaks, so stills alone never clear content). Fixes are cheapest here. Threshold heuristics lose to the pixel diff and neutral reads: textured or sparse layouts that defeat a brightness check get resolved by G3c, not by relaxing the gate.

**G3a — audio mix** (targets in the loudness section below):
```
ffmpeg -i <video> -af ebur128=peak=true -f null NUL      # whole file → integrated + true peak
ffmpeg -ss 47 -t 5 -i <video> -af ebur128=peak=true -f null NUL      # a speech window (seconds)
ffmpeg -ss 1 -t 3 -i <video> -af ebur128=peak=true -f null NUL       # a music-only window (seconds)
```
Read the summary's `I:` (integrated) and `True peak: Peak:` against the targets — true peak needs `peak=true`; the default ebur128 run omits it entirely. (On macOS/Linux use `-f null -`; `NUL` is the Windows spelling.)

**G3b — blank-scene sweep**: per scene, diff the 85%-through frame against the faded-out final frame:
```python
# <video> <scenes.json: [{"start":F,"dur":F},...] → prints per-scene mean abs diff; any ≤3 flags empty
import json,subprocess,sys
from PIL import Image
v,scenes=sys.argv[1],json.load(open(sys.argv[2]))
for s in scenes:
    fs=[]
    for f in (int(s["start"] + s["dur"] * 0.85), int(s["start"] + s["dur"]) - 2):
        subprocess.run(["ffmpeg","-y","-v","error","-i",v,"-vf",f"select=eq(n\\,{f})","-frames:v","1",f"tmp{f}.png"])
        fs.append(Image.open(f"tmp{f}.png").convert("L"))
    d=sum(abs(a-b) for a,b in zip(fs[0].getdata(),fs[1].getdata()))/(fs[0].width*fs[0].height)
    print(s["start"],round(d,2),"EMPTY" if d<=3 else "ok")
```
Any scene flagged EMPTY fails the gate. (The scenes list is the generated timing table — same source of truth. Threshold provenance, measured on a real render: content scenes diff 3.6-4.2, empty/black scenes 0.0-1.3, sparse dark end-cards 1.3-2.5 — the gray zone is exactly what G3c arbitrates. Calibrated at 1080p; on a 540p render halve it, or lean on G3c.)

**G3b′ — first frame**: extract frame 0 and measure it:
```
ffmpeg -y -v error -i <video> -frames:v 1 first.png
python -c "from PIL import Image; import numpy as np; a = np.array(Image.open('first.png').convert('L')).astype(float); print('std', round(a.std(), 1), 'BLANK' if a.std() <= 2 else 'ok')"
```
A near-uniform frame (std ≤ 2 on a flat-background theme) fails. A fade-in envelope on the first scene renders an all-background opening frame, which reads as "loading" on platforms — the first scene enters with no fade-in (a `fadeInFrames=0` branch on the dissolve component; when an envelope argument can be zero, guard the interpolate range's monotonicity — `[0, 0, …]` throws at render time, not at authoring).

**G3c — neutral content reads**: vision-model reads of extracted frames use neutral prompts (describe what is present). A read fails when the description reports blank or black content, or content contradicting what the timing table places at that frame; it passes when the description names the scene's actual content. Deep-dark or sparse layouts that defeat G3b's threshold get resolved here, not by relaxing the gate.

## G4 — final render + artifacts

Render final through the segmented driver — `scripts/render_segments.sh` (strategy in the Final-render section below; 4K path choice: read `remotion-4k-polish` first) — then each artifact's check:

**Covers** — per required ratio, dimensions verified:
```python
# args: cover files → aspect must be ~16:9 or ~4:3 at ≥1080 height (a 1440-wide 4:3 cover is compliant)
from PIL import Image; import sys
for p in sys.argv[1:]:
    im = Image.open(p); ar = im.width / im.height
    ok = im.height >= 1080 and (abs(ar - 16/9) < 0.02 or abs(ar - 4/3) < 0.02)
    print(p, im.size, "OK" if ok else "BAD RATIO OR TOO SMALL")
```
Existence + size per the intake platform list; which ratios and the design rules live in the Covers section below.

**Platform variants** — every variant the intake platform list requires is rendered and passes the same G2 spec check (fps/duration against the timing table; dimensions against the intake-set target for that variant — this is where the 4K/1080p answers get enforced).

**Publish copy** — section presence and every length rule, by `len()` against each platform's counting rule; the limits live in the publish-copy section below (titles within limits, three description versions present, four chapter versions present).

**Ending** — extract the final frame and one ~3s before it (`ffmpeg -sseof -3 -i <video> -frames:v 1 before.png` then `ffmpeg -sseof -0.1 -i <video> -frames:v 1 final.png`); the final frame is the sign-off card (not black), and if the ~3s frame already shows the card, the card exceeds its budget (Ending section).

**Output directory purity** — `ls` the output directory; it contains deliverables and nothing else (no logs, temp stills, partial renders).

## Audio-first timing (narrated videos)

When narration is TTS and intake settled the timing authority as audio-first (the default), the timeline derives from audio, never from design estimates:

1. Write and gate the narration script, then **freeze** it. Every sentence changed after synthesis means re-synthesis, re-timing, and a re-render of everything downstream — confirm with the user before touching a frozen script.
2. Synthesize per-segment audio (tts-forge).
3. Derive timing from measured durations — **by running a script over the segment files, never by hand arithmetic** (hand-computed cumulative starts have produced real off-by-hundreds errors). The derivation, once implemented:
   - scene length = `ceil((segment_duration + pad) × fps)`, pad ≈ 0.7s breathing room
   - scene starts are cumulative; the last segment's end is the composition length
   - caption timing when the narration text is known (the usual TTS case): **whisperx forced alignment** against the real audio — wav2vec2 aligns known text word-accurately; anchor each cue to its speech onset (`silence_end − 150 ms`; cutting at the silence start runs a whole pause late). ASR word timestamps (faster-whisper) are estimates that drift a second or more — never align from them. Any script edit after alignment invalidates the alignment: re-run it and everything derived from it
   - caption spans with no alignable text: detect speech pauses (`ffmpeg silencedetect` at −32dB, ≥0.16s), place each cue boundary at the pause nearest its character-proportional estimate (fall back to the estimate when no pause within 0.7s), convert to frames
4. Scenes and captions consume the generated tables. Proportional rescaling of caption times desyncs against real speech pacing — re-anchor to aligned words, or to pauses when there is no text.
5. When alignment drifts, diagnose on the dry VO track, never the mixed cut (energy detection finds the bed, not the voice — one wrong "-1.6 s constant offset" conclusion came from exactly this); calibrate silence thresholds on pure VO conservatively; keep silence-search windows narrow enough to exclude neighboring segments; verify every window parameter actually passed to the aligner.

## Audio mix baseline (G3a targets)

bilibili transcodes without loudness normalization — what you upload is what viewers hear; YouTube pulls down toward about −14 LUFS and never boosts. Targets for narration-led video:

- Integrated loudness: −14 LUFS ±1 for narration-led video (ear-verified in production; matches YouTube's pull-down target; music-only videos set their own)
- True peak: ≤ −1 dBTP (ebur128 is the authority — loudnorm's tables overstate)
- Music bed: 12-18 dB under the voice; the high end when clarity matters. Both extremes have failed before — deeper beds read as inaudible, a 5-7 dB bed drew viewer complaints of too-loud music — so audition the actual mix's 45s segment before rendering; the user re-tunes per video.
- Verify with an ebur128 three-window read: whole file, a speech window, a music-only window

**Reaching the targets**: condition each VO segment before mixing — measure (ebur128), gain to −14 LUFS/segment, limit; alimiter eats 1-2 dB of applied gain, so iterate measure→gain→remeasure (≤3 rounds). Music selection is its own decision gate: search a library for THIS video (a previous episode's track is not a shortcut), audition 3-5 candidates over the same ~30s segment at matched level, the user picks; normalize the chosen track to −16 LUFS before applying bed curves (skipping it biases the bed ~2.5 dB), and derive the bed-curve coefficients from the target bed level — narrative / data-dense / closing tiers, closing highest — never hardcode them.

## Final-render strategy (every G4 render)

**The segmented driver is the default for finals, whatever the length** — a bare single-process render is the skip-this-step failure mode (one measured run: 58-minute single-process ETA vs 15 minutes through the driver). **Maximize parallelism to the actual hardware — measure, then compute, never accept a default queue count:**

1. Probe: logical CPU count and FREE RAM (not total — a "cleaned" machine frees twice the queues; on Windows read commit-charge headroom, not physical free — physical free understated the available queues 8× on a real machine). Killed renders squat GBs of RAM in orphan ffmpeg/chrome-headless processes before the probe runs — `render_segments.sh` kills the chrome-headless shells at startup and warns on ffmpeg; kill the ffmpeg ones by hand when free RAM looks low (a hand-driven run cleans both by hand first). The shell kill also takes down a concurrently running Remotion render's workers — confirm none is live before launching. Script cleanup and the RAM probe are PowerShell steps; elsewhere, clean and measure by hand.
2. Calibrate on the first render: an instance saturates ~3-4 cores regardless of `--concurrency` (architectural), but its RAM scales with output resolution (~6-8GB at 4K, less at 1080p) — measure one running instance, then compute `queues = min(floor(cores/4), floor(free_ram_gb / measured_instance_gb), remaining_segment_count)`. Two remaining segments means two queues; a third lane has nothing to render. **Pass the computed value as `--queues N`** — the script's auto mode assumes a 4K-sized 7 GB/queue (`--queue-gb` overrides) and floors the division, so on a busy machine it lands on 1 queue and quietly forfeits the parallelism (the measured 15-minute run above needed `--queues 3`). The formula has a measured ceiling: CPU oversubscription bites before RAM on dense machines — 12 queues crashed segments where 6 held on 32 cores, so ~6 is the practical cap; stability beats the formula.

- **Bundle verification around every render that follows code changes**: clear `node_modules/.cache` first (a stale webpack cache renders the old bundle — the tell is the frame count disagreeing with the timing table), run `npx remotion compositions` and confirm frames equal the timing table's totalFrames, and after rendering read one frame off a changed page. `tsc` passing is not verification.

- **Segmented rendering**: split into N frame-exact segments (each an independent encode), render sequentially or in 2-3 parallel instance queues, concat with stream copy. Zero quality loss: same encoder settings per segment, no re-encode at the join. Scripts needing a total duration read it from the generated timing table — a TOTAL hardcoded from the previous timeline shipped audio 8 s longer than the video.
- **Frame-exact acceptance**: after concat, `ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1` equals the timing table's totalFrames. `format=duration` carries the audio track and can overrun the video silently — it is never the frame-count authority.
- **Resume**: segments already on disk are skipped — a crashed run costs only the in-flight segment; which is exactly why a timeline change clears `out/segments/` first (delete by explicit list), or resume splices old-timeline segments into the new cut. One driver instance at a time (step 1's shell-kill warning).
- `render_segments.sh` gates concat on the integrity check itself; a hand-driven segment run needs `scripts/check_segments.sh` first.

## Windows render environment

- A killed render leaves node/chrome-headless-shell/ffmpeg processes alive — the same residue the final-render strategy's step 1 cleans for the RAM probe, plus node instances that lock partial outputs (`rm` reports "Device or resource busy"). For the locked-output case kill by command line — `Get-CimInstance Win32_Process` filtered on `remotion`, `Stop-Process` each — then delete partials.
- Render commands run bare, no pipes: `… | tail` eats the real exit code and a failed render reports success.
- Pass `--port` explicitly — the renderer's internal server defaults to 3000, which collides with WSL port forwarding on dev machines.
- Keep `public/` lean: narration WAVs and screenshots pile into tens of MB and slow every bundle copy. On an intermittent copy timeout, retry once before diagnosing.

## Ending & completion rate

- The video ends when the music ends — fade the audio over the outro and cut. Silent tails and fade-to-black tails both cost completion rate: end on the card, hard cut.
- Sign-off card: ≤2s total, its animation done within ~1s, then straight to the end.
- Closing copy states a takeaway or next action; begging CTAs ("评论区说" / "comment below") read as filler — engagement prompts belong in the pinned comment.
- Platform variant cards (e.g. bilibili triple-action) render as a **composition props variant** inserted before the outro — the variant joins the timeline with native transitions, and both platform versions build from one codebase. (File-level concat of a separately rendered tail is the fallback: it needs aligned streams — e.g. a silent audio track on the tail — and re-checking the join.) A triple-action card gets its own budget: icons pop in fast and asynchronously within ~1s, hard end at ≤2.5s.

## Covers

- Explore before finalizing: produce 3-4 covers with genuinely different visual concepts — different metaphor and information organization. Rearranging the same elements, or reusing video components (a scene's terminal card, the header bar), yields variations of one cover rather than options; the user picks from real alternatives, then the chosen concept gets built out in every required ratio.
- One cover per ratio the intake platform list implies — typically 16:9 (1920×1080) and 4:3 (1440×1080) for bilibili/xiaohongshu; a YouTube-only job needs no 4:3. **A 4:3 cover is its own layout** — vertical space runs out differently, so design it from scratch (move footnotes, re-center blocks, re-fit type); scaling a 16:9 layout down produces wrapped titles and clipped cards.
- Large type only — everything a thumbnail must communicate at ≥48px at 1080-scale. Small text on covers is invisible in feeds; write nothing you wouldn't read at 200px wide.
- The cover's largest word is a category/hook word the thumbnail reads (记忆插件 — not the generic 插件); category detail never demoted into the small line.
- Action words on a cover match what was actually done — no 实测 (tested) unless it was tested.
- Chinese title should be sans/bold (serif CJK reads thin at cover sizes) and at least as prominent as any English title — viewers read the language they know to decide what the video is.
- **Verify by reading, not by metric**: downsampled-pixel brightness checks are blind to thin/colored text (green prompt lines, gray footnotes — all below threshold). Downscale the full cover to ASCII art and read it; this catches wraps, overlaps, and missing elements that metrics pass.
- The cover is an independent design — a frame from the video is not a cover.

## Publish copy

Per-platform deliverable, written after the video is final (facts on screen are then frozen); it lands on disk as `upload.md` — one file carrying the per-platform paste blocks below. Dates in publish copy are absolute (`2026-09-03`, never 昨天/今天) — production-to-publish spans days, so relative dates are stale on arrival. Full spec below — this file owns the spec.

**Plain text inside paste blocks.** Platforms render markdown literally: `**bold**` shows as asterisks, `-` markers show as hyphens. The upload.md file may use markdown for its own sections; the fenced paste-block content is plain text with line breaks, list items as `·` or `1. 2. 3.`.

**Titles — multiple, per platform:**

- **bilibili**: professional, ~30 chars, telling the viewer what happens in the video (e.g. "从零搭建一个全新项目"), with the author's identity when recognizable. A title the viewer needs the description to understand is the wrong title.
- **xiaohongshu**: ≤20 chars, same professional tone, zero marketing language ("大佬带你", "效率翻倍").
- **YouTube**: may carry "(双语字幕)" or the English title variant.

The ~30-char targets are style targets, not platform caps — the bilibili cap is far higher (historically 80). Verify the live cap when a title wants to run long; never assume the shorter.

**Title workflow (production-proven)**: read the channel's existing top-performing titles in the browser first; dispatch ≥3 fresh subagents, each drafting 20 candidates in its own direction (data-driven / impact / plain descriptive), each seeded with those channel titles; hand the full list to the user to pick. A title states what the video covers plus a concrete number — rejected shapes, each on a real production: questions; hooks that withhold the number; format words (指南 / 全解 / 拆解); self-description ("我去读了…"); any promise the video does not deeply cover.

**Description — three versions:**

1. **Full (bilibili/YouTube)**, five parts in order:
   - 定调句 (1-2 sentences): author + what they did + one-sentence value — "X 用 Y 做了 Z", never "来自 X 的讲解".
   - 看点 (numbered): hooks with a teaser, not a table of contents — each item carries suspense, not a flat fact.
   - 关键内容 (`·` list): key beats as "label: content" pairs — a scannable index, easier than a flat list.
   - 来源 (`·` list): `来源：` / `· 作者：` / `· 原视频：` / `· 网站/仓库：` / `· 时间：<video date, e.g. 2026.8.23>` — structured, never inline; the date line goes last.
   - 结尾话术 (verbatim): `字幕：AI 辅助转录 + 翻译并经人工校对。如有不准确之处，欢迎指出。` — for original-narration videos (no translation), the honest adaptation: `字幕与口播：AI 辅助制作并经人工校对。如有不准确之处，欢迎指出。`
2. **xiaohongshu pinned comment (≤300 chars, every character counted as the platform counts)**: the first three paragraphs compressed plus the closing note. Leave out 看点, 关键内容, and links — they eat the budget. Verify with `len()`; compress until it fits.
3. **xiaohongshu body (≤100 chars)**: one sentence — who published what, the core topic, why watch. No metadata ("双语字幕" belongs in the pinned comment). Verify with `len()`.

**Chapters — four versions, all produced (a hard checklist, not a menu):**

1. bilibili platform field (≤10): `HH:MM:SS` + name ≤11 chars
2. xiaohongshu platform field (≤15): same format
3. YouTube platform field: same format
4. Pinned-comment full list: `HH:MM:SS` + one descriptive sentence per chapter, no length limit

Timestamps come from the actual delivered timeline (an audio-first run reads the generated timing table). Tone throughout: translator, not promoter.

**Verify before handover**: title lengths, chapter counts and name lengths, description char counts — each against its platform's counting rule, by `len()`. Re-pull every fast-moving number the description shows (stars, downloads, usage counts) before upload; when the video curates third-party items, run the curation recall audit (materials.md) at the same time.
