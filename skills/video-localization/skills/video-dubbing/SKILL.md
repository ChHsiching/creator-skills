---
name: video-dubbing
description: Replace a video's original English vocals with Chinese voiceover, then re-time the video so the picture matches the Chinese. Use when the user wants to dub a video into Chinese — mentions 中配 / 配音 / 中文配音 / 换原声, or has a cooked bilingual video and wants a second Chinese-narrated release, or another skill (e.g. video-cooking) hands off "video is done with subtitles, add a Chinese dub."
---

Replace a video's original English vocals with **Chinese voiceover**, then **re-time the video** so picture stays in sync with the longer/shorter Chinese. The result is a second release — same picture, Chinese audio, bilingual ZH+EN subtitles burned in.

This skill does the two creative parts the CLI can't: **translating for dubbing** (complete sentences, not the subtitle fragmentation) and **bi-directional re-timing** (slow down or speed up each video segment to match the Chinese audio, never stretching the audio). Deterministic execution (Demucs, ffmpeg, IndexTTS2) is handled by the [`cook`](https://github.com/ChHsiching/video-cook) CLI's `cook dub` subcommand, with this skill's `scripts/` as a fallback.

## When to reach for this skill

You have a video that already has:
- A **raw video file** (`<output-root>/raw/<name>.raw.mp4`) — the original, with English vocals.
- A **bilingual subtitle run** from `video-subtitle` — specifically `transcript/<name>.en.full.srt` (the full-sentence English transcript, merged from whisperX fragments) and `transcript/translations.txt`.

You want a Chinese-dubbed release. If you don't have these yet, run `video-download` then `video-subtitle` first — this skill reads their outputs.

## What you produce

A new `dubbed/` stage folder added to the video's output directory, plus the final products (video + upload subtitle) in `cooked/` and `cloud-srt/`:

1. `transcript/translations_dub.txt` — the dub script (one Chinese line per `en.full.srt` cue, translated for dubbing, not subtitle fragments)
2. `transcript/<name>.zh.dub.srt` — Chinese SRT (timestamps inherited from `en.full.srt`, before re-timing)
3. `dubbed/_reference/ref.wav` — 14-30s clean clip of the original speaker (IndexTTS2 reference)
4. `dubbed/vocals.wav` — original vocals, separated by Demucs
5. `dubbed/no_vocals.wav` — original BGM + SFX (kept for inspection; only mixed when BGM is present)
6. `dubbed/_full/_segments/sent_NNNN.wav` — per-cue IndexTTS2 output (cache, re-usable)
7. `dubbed/_full/timeline.json` — the re-timed timeline (every cue's new start/end on the dubbed video's clock)
8. `dubbed/_full/dub.wav` — the synthesized Chinese dub, placed on the new timeline
9. `dubbed/_full/dubbing.srt` / `dubbing.merged.srt` — Chinese subtitles on the new timeline (working files; merged.srt is the shorten+merge-short version), with `dubbing.en.srt` (full-sentence English on the new timeline), `dubbing.en.short.srt` / `dubbing.en.merged.srt` (its shorten+merge-short outputs) and `dubbing.bilingual.srt` (the biliteral union that actually gets burned) beside them
10. `cooked/<name>.dubbed.mp4` — **the product**: raw video, re-timed, with Chinese dub + burned bilingual (ZH+EN) subtitles
11. `cloud-srt/zh.dub.srt` and `cloud-srt/en.dub.srt` — **the upload subtitles**: copies of `dubbing.merged.srt` and `dubbing.en.merged.srt`, for platforms that accept soft subs (B站云字幕). Named simply, they sit next to `cloud-srt/{zh,en}.srt` from `video-subtitle`.

The run is not done until the final video plays end-to-end with synced audio and readable subtitles — see Step 8.

## Directory layout

This skill adds `dubbed/` (working directory) and writes the final products to `cooked/` and `cloud-srt/`:

```
<output-root>/
├── raw/                            ← from video-download (this skill reads it)
│   └── <name>.raw.mp4
├── transcript/                     ← from video-subtitle (this skill reads + adds)
│   ├── <name>.en.full.srt          ← full-sentence English (the dub script source)
│   ├── translations_dub.txt        ← this skill writes: one Chinese line per cue
│   └── <name>.zh.dub.srt           ← this skill writes: pre-re-timing SRT
├── cooked/                         ← final videos live here
│   ├── <name>.cooked.bar.mp4       ← from video-subtitle (untouched)
│   └── <name>.dubbed.mp4           ← this skill's product
├── cloud-srt/                      ← upload subtitles live here
│   ├── zh.srt                      ← from video-subtitle (untouched)
│   ├── en.srt                      ← from video-subtitle (untouched)
│   ├── zh.dub.srt                  ← this skill's upload subtitle (copy of dubbing.merged.srt)
│   └── en.dub.srt                  ← this skill's upload subtitle (copy of dubbing.en.merged.srt)
└── dubbed/                         ← this skill's working directory
    ├── _reference/
    │   └── ref.wav
    ├── _full/
    │   ├── timeline.json
    │   ├── _segments/              ← per-cue IndexTTS2 cache
    │   ├── _vsegs/                 ← per-segment re-timed video chunks
    │   ├── dub.wav
    │   ├── video_adjusted.mp4      ← re-timed video (before burn)
    │   ├── dubbing.srt             ← working file (ZH, pre-shorten)
    │   ├── dubbing.short.srt       ← working file (ZH, shorten output)
    │   ├── dubbing.merged.srt      ← working file (ZH, post-shorten; copied to cloud-srt)
    │   ├── dubbing.en.srt          ← working file (full-sentence EN on the new clock)
    │   ├── dubbing.en.short.srt    ← working file (EN, shorten output)
    │   ├── dubbing.en.merged.srt   ← working file (EN, post-shorten; copied to cloud-srt)
    │   └── dubbing.bilingual.srt   ← working file (biliteral union; what gets burned)
    ├── vocals.wav
    └── no_vocals.wav
```

Rule: **`dubbed/` is the working directory; `cooked/<name>.dubbed.mp4` and `cloud-srt/{zh,en}.dub.srt` are the products.** Never touch `raw/`, `transcript/<name>.zh.srt`, `cooked/<name>.cooked.mp4`, or `cloud-srt/{zh,en}.srt` — those belong to `video-subtitle`. If this skill fails halfway, the bilingual cooked shipment is still complete.

## The pipeline

The pipeline is implemented in `scripts/full_dub.py`, which takes a `synth|timeline|retime|burn|full` argument so each phase runs independently and resumes from cache. The steps below describe what each stage does; `cook dub <stage> --python <indextts-venv>/Scripts/python.exe` invokes each through cook (which runs full_dub.py as a subprocess under the IndexTTS2 venv), and the scripts run directly as a fallback.

### Step 0 — Resolve the environments

There are **two** Python environments in play, and confusing them is the failure mode this step exists to prevent:

- **cook's environment** (system Python or `~/.venvs/video-tools/`) — where the `cook` CLI lives, with whisperX/yt-dlp/torch for the subtitle pipeline.
- **IndexTTS2's environment** (`~/Git/index-tts/.venv`) — a separate venv holding `indextts`, `torch` (CPU build), and `demucs`. These deps are heavy and isolated on purpose; do **not** try to install them into cook's environment.

cook runs each dub stage as a subprocess under the IndexTTS2 venv via `--python`, so `from indextts import ...` resolves there. **Every `cook dub` command in this skill takes `--python <indextts-venv>/Scripts/python.exe`.** Resolve the venv path once (default `~/Git/index-tts/.venv`) and reuse it for the whole run.

**0a. Probe both environments are reachable:**

```
<cook-venv>/Scripts/cook doctor                                    # whisperX/yt-dlp/ffmpeg
<indextts-venv>/Scripts/python -c "import indextts, demucs; print('ok')"   # indextts + demucs
```

**0b. Single-thread constraint.** IndexTTS2 must run single-threaded (`OMP_NUM_THREADS=1`), or it produces garbage audio. `full_dub.py` sets this internally before importing torch, so you don't need to export it yourself — just don't run two dub stages in parallel.

Done when cook's doctor reports whisperX/yt-dlp/ffmpeg installed, the IndexTTS2 venv imports `indextts` + `demucs`, and you know the absolute path to `<indextts-venv>/Scripts/python.exe` to pass as `--python`.

### Step 1 — Separate vocals from the raw video

The original audio is one mixed track (vocals + BGM + SFX). Demucs splits it so we can extract a clean reference and check for BGM later.

```
cook dub separate <output-root> <name> [--model htdemucs] --python <indextts-venv>/Scripts/python.exe
```

Demucs lives in the IndexTTS2 venv, so `--python` points there. Use `htdemucs` (single model, ~3GB RAM), not `htdemucs_ft` (bag of 4 models, ~20GB RAM — OOMs on 32GB machines). Quality is slightly lower but adequate for reference extraction.

In foreground mode (default), cook moves the separated stems to `dubbed/vocals.wav` + `dubbed/no_vocals.wav` automatically; in `--detach` mode you move them yourself after the done marker appears.

Done when `dubbed/vocals.wav` AND `dubbed/no_vocals.wav` both exist with duration matching raw ±0.5s.

### Step 2 — Extract the reference clip

IndexTTS2 needs a **14-30 second** clean clip of the original speaker. Longer than the old VoxCPM2 requirement (8s) because IndexTTS2 clones prosody, not just timbre — it needs more material to learn rhythm.

Run the skill's `extract_reference.py` against `vocals.wav`:

```bash
<indextts-venv>/Scripts/python <skill>/scripts/extract_reference.py \
    <output-root>/dubbed/vocals.wav \
    <output-root>/dubbed/_reference/
```

The script uses whisperX internally to transcribe the reference clip, so it needs a venv with whisperX — the IndexTTS2 venv has it (alongside indextts/demucs), so reuse that one for consistency.

The script finds the longest continuous speech region (no silence gaps > 0.3s) within 14-30s. If no single region is long enough, it picks the densest 14s window. Override by dropping a `.wav` into `voices/` or passing a custom path.

Done when `dubbed/_reference/ref.wav` exists, is 14-30s, 16kHz mono, and contains continuous speech (no long silences).

### Step 3 — Translate for dubbing (the agent does this)

This is where dubbing diverges from subtitles. **Do not use `translations.txt`** (the subtitle translation) — it follows whisperX's 151-fragment cuts, which split sentences. Dubbing needs **complete sentences** so the Chinese flows naturally when spoken.

Read `<output-root>/transcript/<name>.en.full.srt` (the full-sentence English transcript — produce it from `en.srt` via video-subtitle's `scripts/make_full_srt.py`; 141 cues for an 11-min video, each one complete sentence). Translate each cue yourself, writing to `transcript/translations_dub.txt` — **one Chinese line per English cue, line N = cue N**.

**The remaining stages (Step 4 synth → Step 5 timeline → Step 6 retime → Step 7 burn) are all implemented in `scripts/full_dub.py` and invoked through cook:**

```
cook dub synth    <root> <name> --python <indextts-venv>/Scripts/python.exe
cook dub timeline <root> <name> --python <indextts-venv>/Scripts/python.exe
cook dub retime   <root> <name> --python <indextts-venv>/Scripts/python.exe
cook dub burn     <root> <name> --python <indextts-venv>/Scripts/python.exe
# or all four at once:
cook dub full <root> <name> --python <indextts-venv>/Scripts/python.exe
```

The steps below describe what each stage does internally (so you can verify outputs and diagnose failures); the `cook dub <stage>` commands above are how you run them.

**Dubbing translation principles** (different from subtitle translation):

- **Translate complete thoughts, not fragments.** The English is already full sentences (that's what `en.full.srt` is). Match that — your Chinese cue is one complete thought.
- **Let length be natural.** Don't pad to fill the time window (the re-timing in Step 5 handles mismatches), and don't compress to fit (you'll lose meaning). Translate faithfully; the algorithm absorbs ±30%.
- **Keep technical terms in English where Chinese devs do** — spec, plan, prototype, agent, token, compact, Wayfinder, grilling, skill, session, ticket, branch, route, etc. See **[REFERENCE.md → "Term retention list"](REFERENCE.md)** for the full set.
- **Keep English for anything shown on screen.** If the speaker says "I'll search for model" and types "model" into a search box visible in the video, keep "model" — translating it to "模型" while the screen shows "model" disorients the viewer. Same for UI labels, code, URLs, filenames.
- **Translate concepts that have standard Chinese names** — 数据模型 (data model), 快照 (snapshot), 选择器 (picker), 选项 (option). When a term has a common Chinese name and isn't shown on screen, use it.
- **Line count must equal cue count.** 141 English cues = 141 Chinese lines — while translating, keep the two files index-aligned. The sanctioned way to change counts is Step 3a's `build_merge.py`, which rewrites both files together.

Then generate the pre-re-timing SRT (timestamps inherited from `en.full.srt`):

```bash
python <skill>/scripts/make_zh_dub_srt.py <output-root>/transcript/<name>.en.full.srt \
    <output-root>/transcript/translations_dub.txt \
    <output-root>/transcript/<name>.zh.dub.srt
```

**Self-review — two passes, mandatory** (same discipline as `video-subtitle` Step 3):
- **Pass 1**: read every line as a spoken sentence. Does it sound like something a person would say?
- **Pass 2**: scan for term-retention errors — every on-screen label, search term, UI element kept in English; every standard-concept term in Chinese. Cross-check against the term-retention list in REFERENCE.md.

**Quality gate — fan-out subagent review (mandatory, before synth).** The self-review passes above are you checking your own work; this gate is a **separate subagent** reviewing it cold. Fan out a subagent with read access to both `<name>.en.full.srt` and `translations_dub.txt`, and ask it to check, for every cue:

1. **Translation accuracy** — does the Chinese faithfully convey the English sentence's meaning? No dropped clauses, no added content, no mistranslations.
2. **Proper-noun spelling** — names (people, products, companies) spelled exactly as the source uses them. "Claude" not "克劳德", "IndexTTS" not "索引TTS", unless a standard Chinese name genuinely exists.
3. **TTS readability** — will IndexTTS2 pronounce this naturally? No awkward character sequences, no orphaned punctuation, numbers and symbols written the way they should be spoken.

The review must happen **before** Step 4 (synth) because TTS is the expensive step (~3.5 min per cue — 141 cues ≈ 8h) — a translation error caught after synth means re-synthesizing every corrected cue. **Read every line of both files; do not pattern-match against known-error shapes** (regex-style scanning for "looks wrong" misses the subtle errors that actually ship — a dropped 的, a misspelled proper noun, a clause that drifted). The subagent's completion criterion: it has read every cue pair end-to-end and either confirms each is correct or lists the specific cue indices that need fixing. Fix anything it flags, then re-run the gate on the changed lines only.

Done when `translations_dub.txt` has the same line count as `en.full.srt` cues, `<name>.zh.dub.srt` exists, both self-review passes pass, **and** the fan-out subagent review has confirmed every cue.

### Step 3a — Pace the script: write long, merge the rest

IndexTTS2 renders standalone short lines (≤8 ZH syllables) at narration pace (~2.6 syll/s vs ~4.3 for 9-20 syllables) regardless of the reference clip — the model's speed control (`speed_emb`) is a zero-initialized dead parameter. Banter-heavy talks (audience asides, "raise your hand" beats) are full of such lines. Handle them BEFORE synth, in this order:

0. **Write longer lines while translating.** Prefer a naturally fuller sentence over clipped shorthand ("这一段是真的太熬人了" not "太熬人了") — no padding, no filler, but don't compress to fragments the model will read like a title card.
1. **Merge what remains short.** Run `python <skill>/scripts/build_merge.py <output-root> <name>` — it groups adjacent cues into 9-24-syllable units (gap ≤1.5s, band ≤24 syllables), backs up originals as `*.v1`, snapshots any existing synth audio to `_segments_orig`, and pre-populates the audio cache from that snapshot so `cook dub synth` only fills the merged groups. **Merged groups must be synthesized with the SAME reference clip as the reused audio** — swapping references changes the timbre audibly. Merged audio plays as one unit; the subtitle pipeline re-splits it for display automatically.

**Pre-synth ear gate (mandatory before committing the run).** Synthesis costs ~3.5 min/cue (240 cues ≈ 14h) and nothing downstream hears audio — the only gate before that spend is the user's ear. Build the pilot as a scratch run: a temp output-root holding a 3-line `en.full.srt` + `translations_dub.txt` (shortest interjection ×2 + one mid sentence), the chosen `ref.wav` in `dubbed/_reference/`, then `cook dub synth` on it (~10 min single-threaded). Hand the wavs to the user and get an explicit OK on voice AND pace. Reference choice shapes delivery pace, not just timbre: prefer a mid-tempo explanatory section — `extract_reference.py` picking the *longest* continuous speech systematically selects the slowest, most deliberate section a talk contains.

Done when `*.v1` backups exist (when merging ran), `translations_dub.txt` line count equals `en.full.srt` cue count post-merge, `<name>.zh.dub.srt` regenerated from the merged files when merging ran (re-run `make_zh_dub_srt.py` — the Step 3 output was built from pre-merge inputs), and the ear gate has an explicit user OK on voice AND pace.

### Step 4 — Synthesize the Chinese dub (the slow step)

IndexTTS2 synthesizes each cue. **Single-threaded only** — multi-threaded inference produces garbage audio (0.05s truncated outputs) due to a float-reduction non-determinism in `SeamlessM4TFeatureExtrator`'s FFT. See **[REFERENCE.md → "The single-thread constraint"](REFERENCE.md)**.

```bash
cook dub synth <output-root> <name> --python <indextts-venv>/Scripts/python.exe
```

`stage_synth` sets `OMP_NUM_THREADS=1` + `torch.set_num_threads(1)` before importing torch (load-bearing — order matters), loads IndexTTS2 once, then synthesizes each cue. Output is `dubbed/_full/_segments/sent_NNNN.wav`, cached by cue index — the cache is NOT text-aware: a cue whose text (or reference) changed re-synthesizes only after you delete its cached wav.

**Pacing policy (replaces the old blanket DSP ban).** Two iron rules: **(1) normal-rate audio is untouchable** — never time-stretch, never atempo; length mismatches are absorbed on the video side. **(2) Slow audio must never drag the video slow** — fix the audio first, don't stretch the picture to cover it. Per cue:

| situation | audio | video |
|---|---|---|
| rate normal, audio ≤ window | untouched | speed up (drop redundant frames) |
| rate normal, audio > window | untouched | stretch capped at **1.15x**; the audio tail bleeds into the following pause (see Step 5's adjuster) |
| rate slow even after the Step 3a merge | fix audio first (ladder below) | only after the audio is normal |

Speed-up ladder for slow cues, cheapest first: re-synthesize with rewritten text (delete the cue's cached wav first — the cache is index-keyed; merge, and pilot comma-rewriting — every `。` the model reads as a deliberate close, so "…，我也是，太熬人了" may pace like one sentence — unvalidated, cheap to try) → synthesize several takes and keep the fastest → DSP `atempo` using the per-cue factors `rate_report.py` prints (target clamped to 4.2-5.5 syll/s; factor ≤ 1.6 — beyond that speech artifacts; silenceremove stays banned outright: it truncates normal speech). Any DSP pass requires the user's ear on samples first.

**Post-synth rate gate (mandatory, before retime).** Run `python <skill>/scripts/rate_report.py <output-root> <name>` right after `cook dub timeline` (Step 5) builds the timeline.json it reads — it buckets per-cue syllables/audio-seconds, applies the policy target, and lists slow cues with suggested factors. `VERDICT: WARN` (exit 1) ⇒ pause and report to the user; `VERDICT: PASS` ⇒ proceed — the listed slow cues are inputs to the speed-up ladder, not blockers. **Any ladder fix that changes audio (re-synthesis or DSP) invalidates timeline.json** — its `zh_dur` values were measured from the wavs you just replaced. After audio fixes: re-run `cook dub timeline`, re-run `adjust_timeline.py`, re-run `rate_report.py`; only then proceed to retime (retime validates cached `_vsegs` durations against the current plan and regenerates stale ones automatically).

**Cost is per CUE, not per minute of video.** Synthesis runs at ~3.5 min/cue regardless of cue length (RTF ~30-36; a 5s cue takes ~3 min); retime costs ~30-90s per *interpolated* segment. Quote the user `cues × 3.5 min + retime 1.5-5h` before starting — an 18-min talk with 240 cues is ~14h of synthesis where an 11-min/141-cue video is ~8h.

Done when `dubbed/_full/_segments/sent_NNNN.wav` exists for every cue AND each is > 1KB (not a truncated garbage file). The synth log's completion line is `Stage 1 DONE: <n> cues synthesized`.

### Step 5 — Bi-directional re-timing (the core innovation)

This is what makes the dub watchable. The Chinese audio is **never stretched** — it plays at its natural TTS speed. Instead, **each video segment is re-timed** to match the Chinese:

For each cue, compute `ratio = chinese_duration / english_window`:
- **ratio < 1 (Chinese shorter)**: **speed up** the video segment (drop redundant frames). No audio change.
- **ratio > 1 (Chinese longer)**: **slow down** the video segment (stretch the picture). No audio change.
- **ratio ≈ 1**: no change.

**Why this beats atempo-stretching the audio** (the old approach): stretched TTS audio sounds unnatural (chipmunk at >1.3x, drawl at <0.8x). Re-timed video looks fine — viewers don't notice 1.2x speedup or 0.7x slowdown on a talking-head video, but they immediately hear stretched speech.

**The string-of-pearls timeline** (prevents audio overlap and subtitle collision):

Build a new linear timeline where each cue plays back-to-back with its neighbors, gaps preserved from the original:
1. For each cue, the new segment duration = the Chinese TTS duration (audio never changes).
2. For each gap between cues, the new gap duration = the original gap (preserves rhythm).
3. Each cue's `new_start` = sum of all preceding segments' new durations — strictly monotonically increasing, mathematically impossible to overlap.
4. Each video segment is cut from the raw video at its original `[start, end]`, then `setpts` re-times it to the new duration.

Run the timeline builder:

```bash
cook dub timeline <output-root> <name> --python <indextts-venv>/Scripts/python.exe
```

Done when `timeline.json` exists, every cue's `new_start < new_end`, no two cues overlap, and the total new duration is within ±50% of the raw (a healthy dub is 10-30% longer or shorter than the original).

**Gap-absorbing cap (recommended whenever short cues exist).** After `cook dub timeline`, run `python <skill>/scripts/adjust_timeline.py <output-root>/dubbed/_full/timeline.json --max-stretch 1.15` BEFORE retime: it caps every cue's video stretch at 1.15x and lets the audio overrun bleed into the following pauses (the burned ZH subtitle window extends to the audio end automatically). `--first-cue-1x` keeps the opening line at exactly 1.0x — first impressions decide swipe-away; `--force1x-file <file>` (one cue index per line) forces 1.0x for a listed set of cues. It asserts tiling/monotonicity/audio-no-overlap; on violation it refuses rather than emit a broken timeline.

### Step 6 — Re-time the video segments + interpolate slow segments

Cut the raw video into segments (cues + gaps), re-time each, and interpolate frames on slowed segments to maintain 60fps.

```bash
cook dub retime <output-root> <name> --python <indextts-venv>/Scripts/python.exe
```

For each segment:
- **Speed-up segment (ratio<1)**: `setpts=factor*PTS` only. The source has redundant frames at 60fps; dropping them is invisible.
- **Slow-down segment (ratio>1)**: `setpts=factor*PTS,minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:me=epzs:vsbmc=1`. The `setpts` stretches the timeline (each source frame displays longer), then `minterpolate` inserts motion-compensated intermediate frames to maintain 60fps. Without interpolation, slowed segments look choppy (15-35fps effective).

**Known limitation**: `minterpolate`'s optical-flow estimation fails on fast non-rigid motion — waving hands leave after-image artifacts (two ghosted hands). This is an architectural limitation of optical flow, not a tunable parameter. On talking-head videos (the common case) it's acceptable; on action footage it's not. The user has accepted this trade-off — see REFERENCE.md for alternatives that don't (no interpolation = choppy but no artifacts).

**Cost**: interpolated segments run at RTF ~23 on CPU. A video with ~90 slowed segments (the typical count) takes ~3 hours. This is the second slow step after TTS.

Done when `_vsegs/v_NNNN.mp4` exists for every timeline segment AND the segment count matches timeline length.

### Step 7 — Assemble audio, subtitles, and burn

Concatenate the re-timed video segments, place the Chinese audio on the new timeline, generate subtitles, and burn.

**7a. Concat segments + place audio** — `cook dub burn` runs the full assembly (concat re-timed segments, place Chinese audio on the new timeline by sequential pad+concatenate assembly, generate subtitles, burn) in one stage:

```bash
cook dub burn <output-root> <name> --python <indextts-venv>/Scripts/python.exe
```

Produces `cooked/<name>.dubbed.mp4` and `video_adjusted.mp4` + `dub.wav` (intermediates under `dubbed/_full/`).

**7b–7c are inside `cook dub burn`.** The same command also generates the subtitles and burns them — you do not run those steps by hand. It runs the same pipeline as `video-subtitle`'s bilingual release, on the dub's re-timed clock:

- **Bilingual subtitle layout, same as the bilingual release.** The Chinese goes through `shorten` + `merge-short`; the full-sentence English (`dubbing.en.srt`, built from `en.full.srt` texts mapped onto the timeline's new cue windows — index-aligned by construction, since cue i's window is exactly where its Chinese audio plays) is unioned with it via `biliteral`; the result burns in the same 220px bottom bar and fonts as the bilingual release (`subtitles.py`'s bottom-bar defaults — no overrides, so the two can't drift). The union's repetition is role-swapped here: EN spans whole sentences while ZH fragments inside them, so **EN repeats across consecutive ZH cues by design** — the mirror of the bilingual release, where ZH repeats across EN fragments.
- **Upload subtitles**: `cook dub burn` copies the merged Chinese to `cloud-srt/zh.dub.srt` and the retimed English to `cloud-srt/en.dub.srt` — same convention as `video-subtitle`'s `cloud-srt/{zh,en}.srt`. Simple names, sit next to their siblings, easy to find at upload time.

**Quality gate — fan-out subagent review of the burned dub subtitles (mandatory, after `cook dub burn`).** What gets burned is the biliteral union of `zh.dub.srt` + `en.dub.srt`, and both ship as upload subtitles — errors here are the most visible kind, on screen for the whole video. After `cook dub burn` produces them, fan out a subagent with read access to `cloud-srt/zh.dub.srt` and `cloud-srt/en.dub.srt` and ask it to check:

1. **Split words** — a single Chinese word or English term broken across two cues by `shorten`, so the viewer sees a fragment on its own (e.g. "数据" / "模型" split across cues when it should be one "数据模型" line). Each cue should read as a complete, self-contained thought.
2. **Adjacent duplicates** — the same line (or near-duplicate) appearing in two consecutive cues. **EN repetition is structural here**: a full-sentence EN cue spans several fragmented ZH cues, so the same English line on consecutive cues is the design (read the `[biliteral] timestamp-union` log line to confirm the union path). The defect is a cue whose ZH **and** EN are both verbatim identical to the previous cue's.
3. **Missing cues** — gaps in the cue numbering, or cues with empty text. A dropped cue means a stretch of video with no subtitle at all.

**Read every cue end-to-end; do not pattern-match against known-error shapes.** The `shorten`/`merge-short` transforms produce cues that look superficially similar (many start with the same particles), so regex-style scanning flags false positives and misses the real errors — a duplicate that differs by one character, a split that lands mid-clause rather than mid-word. The subagent's completion criterion: it has read every cue top to bottom and either confirms the file is clean or lists the specific cue numbers with their problem.

This gate sits **after** `cook dub burn` (the merged subtitles only exist once burn runs it). Translation-content errors were already gated in Step 3; this gate catches the `shorten`/`merge-short`/union artifacts. If it finds any, fix `cloud-srt/zh.dub.srt` and the in-`dubbed/_full/` source, then re-run `cook dub burn`.

Done when `cooked/<name>.dubbed.mp4` exists, duration matches the new timeline ±0.5s, a spot-check frame at a speaking timestamp shows bilingual subtitles rendered in the bottom bar (EN above ZH), **and** the quality gate above has cleared.

### Step 8 — Verify

Play the video end-to-end (or spot-check at 5-6 timestamps). Check:
- **Audio-video sync**: the Chinese audio matches the speaker's lip movements and on-screen actions.
- **Subtitle readability**: no single line overflows the screen (sample frames at different points — if you see text clipped at left/right edges, the `shorten` max-zh is too high for this font size).
- **Slow-segment smoothness**: the interpolated segments play without obvious stutter. Hand-motion artifacts are expected and accepted.
- **No audio gaps or overlaps**: every cue has audio, no two cues play simultaneously.

Then report to the user:
- The absolute path of `<name>.dubbed.mp4`.
- The reference clip used (so they can sanity-check the voice).
- The total duration change (e.g. "11min → 12.4min, +13%").
- The number of cues that needed slow-down interpolation.

Done when the video plays clean end-to-end. The run is not done until this passes.

## Reference

The following details are pushed out of this file because they're consulted on demand:

- **[REFERENCE.md](REFERENCE.md)** — IndexTTS2 install (the single-thread constraint, the garbage-audio bug, model download), the full term-retention list (which English terms stay English, which become Chinese, and the on-screen-content rule with examples), the **timeline.json schema** (segment fields and invariants for tools that edit it), Demucs raw commands, the bi-directional re-timing math (ratio formula, the string-of-pearls construction proof), `minterpolate` parameter tuning and its artifact alternatives (blend mode, no-interpolation), the IndexTTS2 vs VoxCPM2 vs 豆包 API comparison (why IndexTTS2 won), and the Chinese-dub quality self-check (洋腔 detection, term-translation audit).
