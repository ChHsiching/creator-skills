---
name: video-dubbing
description: Replace a video's original English vocals with Chinese voiceover on an identity timeline — the video keeps its original speed and duration, each cue's Chinese audio is fitted into its original window. Use when the user wants to dub a video into Chinese — mentions 中配 / 配音 / 中文配音 / 换原声, or has a cooked bilingual video and wants a second Chinese-narrated release, or another skill (e.g. video-cooking) hands off "video is done with subtitles, add a Chinese dub."
---

Replace a video's original English vocals with **Chinese voiceover** on an **identity timeline**: the video is never re-timed — every frame keeps its original timestamp and the dubbed release has exactly the raw video's duration. Each cue's synthesized audio is fitted into its own original window (cue start → next cue's start) with a per-cue atempo; faster or slower synthesis both land in the window. The result is a second release — same picture at the same speed, Chinese audio, bilingual ZH+EN subtitles burned in.

This skill does the two creative parts the CLI can't: **translating for dubbing** (complete sentences written to a char budget, not the subtitle fragmentation) and **running the quality gates** (length gate, cold review, ear gate, post-burn review). Deterministic execution (Demucs, IndexTTS2, assembly, ffmpeg) is handled by the [`cook`](https://github.com/ChHsiching/video-cook) CLI's `cook dub` subcommand, with this skill's `scripts/` as a fallback.

## When to reach for this skill

You have a video that already has:
- A **raw video file** (`<output-root>/raw/<name>.raw.mp4`) — the original, with English vocals.
- A **bilingual subtitle run** from `video-subtitle` — specifically `transcript/<name>.en.full.srt` (the full-sentence English transcript, merged from whisperX fragments) and `transcript/translations.txt`.

You want a Chinese-dubbed release. If you don't have these yet, run `video-download` then `video-subtitle` first — this skill reads their outputs.

## What you produce

Three products ship: `cooked/<name>.dubbed.mp4` (raw video untouched, Chinese dub, burned bilingual subtitles — duration identical to the raw), `cloud-srt/zh.dub.srt` + `en.dub.srt` (upload subtitles). Everything else is working files under `dubbed/` — the annotated tree below maps every one of them.

The run is not done until Step 6's checks pass.

## Directory layout

This skill adds `dubbed/` (working directory) and writes the final products to `cooked/` and `cloud-srt/`:

```
<output-root>/
├── raw/                            ← from video-download (this skill reads it)
│   └── <name>.raw.mp4
├── transcript/                     ← from video-subtitle (this skill reads + adds)
│   ├── <name>.en.full.srt          ← full-sentence English (the dub script source)
│   ├── translations_dub.txt        ← this skill writes: one Chinese line per cue
│   └── <name>.zh.dub.srt           ← this skill writes
├── cooked/                         ← final videos live here
│   ├── <name>.cooked.bar.mp4       ← from video-subtitle (untouched)
│   └── <name>.dubbed.mp4           ← this skill's product
├── cloud-srt/                      ← upload subtitles live here
│   ├── zh.srt / en.srt             ← from video-subtitle (untouched)
│   └── zh.dub.srt / en.dub.srt     ← this skill's upload subtitles
└── dubbed/                         ← this skill's working directory
    ├── _reference/
    │   └── ref.wav
    └── _full/
        ├── _segments/              ← per-cue IndexTTS2 cache
        ├── dub.wav                 ← the dub on the original clock
        ├── dubbing.srt             ← working file (ZH, pre-shorten)
        ├── dubbing.short.srt       ← working file (ZH, shorten output)
        ├── dubbing.merged.srt      ← working file (ZH, post-shorten; copied to cloud-srt)
        ├── dubbing.en.srt          ← working file (full-sentence EN)
        ├── dubbing.en.short.srt / dubbing.en.merged.srt  ← its shorten+merge-short outputs
        ├── dubbing.bilingual.srt   ← working file (biliteral union; what gets burned)
        ├── dubbing.cooked.ass     ← working file (ass output, copied to burn.ass)
        └── burn.ass                ← the ASS actually burned
```

Rule: **`dubbed/` is the working directory; `cooked/<name>.dubbed.mp4` and `cloud-srt/{zh,en}.dub.srt` are the products.** Never touch `raw/`, `transcript/<name>.zh.srt`, `cooked/<name>.cooked.mp4`, or `cloud-srt/{zh,en}.srt` — those belong to `video-subtitle`. If this skill fails halfway, the bilingual cooked shipment is still complete.

## The pipeline

Two stages after the creative work: **synth** then **assemble**, implemented in `scripts/full_dub.py` and invoked through cook:

```
cook dub synth    <root> <name> --python <indextts-venv>/Scripts/python.exe
cook dub assemble <root> <name> --python <indextts-venv>/Scripts/python.exe [--keep-subs]
# or both:
cook dub full <root> <name> --python <indextts-venv>/Scripts/python.exe
```

The steps below describe what each stage does internally (so you can verify outputs and diagnose failures); the `cook dub <stage>` commands are how you run them.

### Step 0 — Resolve the environments

There are **two** Python environments in play, and confusing them is the failure mode this step exists to prevent:

- **cook's environment** (system Python or `~/.venvs/video-tools/`) — where the `cook` CLI lives, with whisperX/yt-dlp/torch for the subtitle pipeline.
- **IndexTTS2's environment** (`~/Git/index-tts/.venv`) — a separate venv holding `indextts`, `torch`, `demucs`, and `whisperx` (the dub pipeline adds the last two on top of upstream's lockfile). These deps are heavy and isolated on purpose; do **not** try to install them into cook's environment.

cook runs each dub stage as a subprocess under the IndexTTS2 venv via `--python`, so `from indextts import ...` resolves there. **Every `cook dub` command in this skill takes `--python <indextts-venv>/Scripts/python.exe`.** Resolve the venv path once (default `~/Git/index-tts/.venv`) and reuse it for the whole run.

**0a. Probe both environments are reachable:**

```
<cook-venv>/Scripts/cook doctor                                    # whisperX/yt-dlp/ffmpeg
<indextts-venv>/Scripts/python -c "from indextts.infer_v2_5 import IndexTTS2; import demucs, whisperx; print('ok')"   # indextts (v2.5) + demucs + whisperx
```

**0b. Single-thread constraint.** IndexTTS2 must run single-threaded (`OMP_NUM_THREADS=1`), or it produces garbage audio. `full_dub.py` sets this internally before importing torch, so you don't need to export it yourself.

Done when cook's doctor reports whisperX/yt-dlp/ffmpeg installed, the IndexTTS2 venv imports `indextts` (v2.5) + `demucs` + `whisperx`, and you know the absolute path to `<indextts-venv>/Scripts/python.exe` to pass as `--python`.

### Step 1 — Separate vocals from the raw video

The original audio is one mixed track (vocals + BGM + SFX). Demucs splits it so we can extract a clean reference and check for BGM later.

```
cook dub separate <output-root> <name> [--model htdemucs] --python <indextts-venv>/Scripts/python.exe
```

Demucs lives in the IndexTTS2 venv, so `--python` points there. Use `htdemucs` (single model, ~3GB RAM), not `htdemucs_ft` (bag of 4 models, ~20GB RAM — OOMs on 32GB machines). Quality is slightly lower but adequate for reference extraction.

In foreground mode (default), cook moves the separated stems to `dubbed/vocals.wav` + `dubbed/no_vocals.wav` automatically; in `--detach` mode you move them yourself after the done marker appears.

Done when `dubbed/vocals.wav` AND `dubbed/no_vocals.wav` both exist with duration matching raw ±0.5s.

### Step 2 — Extract the reference clip

IndexTTS2 needs a **14-30 second** clean clip of the original speaker — it reads at most the first 15s, so a full-cap window beats a short one. IndexTTS2 clones **prosody, not just timbre**: the window's delivery pace becomes the whole dub's delivery pace. The default picker takes the longest continuous speech, which tends to select the slowest, most deliberate passage — often wrong. Prefer the scanner:

```bash
<indextts-venv>/Scripts/python <skill>/scripts/scan_reference.py \
    <output-root>/dubbed/vocals.wav --out <output-root>/dubbed/_reference/ \
    [--full-band <output-root>/raw/<name>.raw.mp4]
```

It ranks fixed 15s windows by syllable rate (density- and pause-filtered) and cuts the top 3 candidates (plus full-band 48k copies with `--full-band`). Still run `extract_reference.py` when you want the densest-window default, and either way: **the user's ear picks the reference, always** — synthesize the pilot sentences once per candidate (Step 3a), score the takes objectively with `scan_reference.py --score take1.wav take2.wav --anchor <anchor.wav>` (anchor = any real clip of the speaker — similarity to the *speaker*, not to the reference clip, is what you are choosing), then hand the wavs to the user.

Done when `dubbed/_reference/ref.wav` exists, is 14-30s, and has no silence gap > 0.3s (`ffmpeg -af silencedetect`).

### Step 3 — Translate for dubbing (the agent does this)

This is where dubbing diverges from subtitles. **Do not use `translations.txt`** (the subtitle translation) — it follows whisperX's fragment cuts, which split sentences. Dubbing needs **complete sentences** so the Chinese flows naturally when spoken.

Read `<output-root>/transcript/<name>.en.full.srt` (the full-sentence English transcript). Translate each cue yourself, writing to `transcript/translations_dub.txt` — **one Chinese line per English cue, line N = cue N**.

**The char budget rule — the core of dub translation.** Each cue's budget is `window seconds × normal speech rate`, fixed **before** you write: the window is cue start to the next cue's start (window + following pause), the rate is a normal reading pace (~4.5-5 syllables/s; a given reference clip measured once at the pilot is a fine rate too — same voice + same `DUB_DURATION_FACTOR`, reusable across videos). Write **to the budget**: slightly over is fine, notably under is not — whatever the synthesized audio actually does, the assembler's per-cue atempo lands it in the window, but text far from the budget means audibly rushed or seconds of dead air. How to fill a budget legitimately (and what "filling" is *not* allowed to invent): **[REFERENCE.md → "Filling the char budget"](REFERENCE.md)**.

**Translation principles** (beyond the budget):

- **Translate complete thoughts, not fragments.** The English is already full sentences; your Chinese cue is one complete thought.
- **Keep technical terms in English where Chinese devs do** — spec, plan, prototype, agent, token, skill, session, branch, route, etc. See **[REFERENCE.md → "Term retention list"](REFERENCE.md)**.
- **Keep English for anything shown on screen** — UI labels, code, URLs, filenames. Examples in **[REFERENCE.md → "Term retention list"](REFERENCE.md)**.
- **Translate concepts that have standard Chinese names** when they aren't shown on screen — the worked examples live in the term-retention list.
- **Line count must equal cue count.** The sanctioned way to change counts is Step 3a's `build_merge.py`, which rewrites both files together.

Then generate the pre-assembly SRT (timestamps inherited from `en.full.srt`):

```bash
python <skill>/scripts/make_zh_dub_srt.py <output-root>/transcript/<name>.en.full.srt \
    <output-root>/transcript/translations_dub.txt \
    <output-root>/transcript/<name>.zh.dub.srt
```

**Self-review — two passes, before the mechanical gate:** read every line aloud in your head as a spoken sentence (does it sound like something a person would say?); then scan the term list below against every line (anything on-screen stays English, standard concepts go Chinese). These are you checking your own work; the subagent review below is the cold read.

**Length gate — mechanical** (pure arithmetic, takes a second):

```bash
python <skill>/scripts/length_gate.py <output-root> <name>
```

It cross-checks every line against its cue window three ways: **short lines** (≤8 syllables — IndexTTS2's narration-pace trap, rewrite fuller or let Step 3a merge), **budget misses** (estimated speech far over its window — text must be cut back — or far under — the window gets dead air, fill it), and the **coverage total** (Σ estimated speech / Σ windows — a uniformly thin translation passes every line check and still dubs to long silences; healthy 90-105%). Exit 1 lists the lines and the coverage verdict; rewrite and rerun until it passes.

**Quality gate — fan-out subagent review (mandatory, before synth).** The ear gate and this review are the only gates before hours of synthesis. Fan out a subagent with read access to both `<name>.en.full.srt` and `translations_dub.txt`, and ask it to check, for every cue:

1. **Translation accuracy** — does the Chinese faithfully convey the English? No dropped clauses, no added content (nothing the English doesn't say), no mistranslations.
2. **Proper-noun spelling** — names (people, products, companies) exactly as the source uses them. "Claude" not "克劳德", "IndexTTS" not "索引TTS", unless a standard Chinese name genuinely exists.
3. **TTS readability** — will IndexTTS2 pronounce this naturally? No awkward character sequences, no orphaned punctuation, numbers written the way they should be spoken.

**Read every line of both files; do not pattern-match against known-error shapes.** The subagent's completion criterion: it has read every cue pair end-to-end and either confirms each is correct or lists the specific cue indices that need fixing. Fix anything it flags, then re-run the gate on the changed lines only.

Done when `translations_dub.txt` has the same line count as `en.full.srt` cues, `<name>.zh.dub.srt` exists, the length gate passes (including coverage), both self-review passes pass, **and** the fan-out subagent review has confirmed every cue.

### Step 3a — Pace the script and win the ear gate

IndexTTS2 renders standalone short lines (≤8 ZH syllables) at narration pace, regardless of the reference clip (the length gate's short-line trap). Banter-heavy talks are full of such lines. Handle them BEFORE synth: **write fuller sentences while translating** ("这一段是真的太熬人了" not "太熬人了"), then run `python <skill>/scripts/build_merge.py <output-root> <name>` to merge what remains short into 9-24-syllable units (backs up originals as `*.v1`, pre-populates the synth cache; merged groups must keep the SAME reference clip). Re-run `make_zh_dub_srt.py` after merging.

**Ear gate (mandatory before the full synth).** Synthesis costs ~3.5 min per cue and nothing downstream hears audio — the only gate before that spend is the user's ear. Build the pilot as a scratch run: a temp output-root holding a 3-line `en.full.srt` + `translations_dub.txt` (a short interjection, a mid sentence, a long one — the same tiers the real script has), the chosen `ref.wav` in `dubbed/_reference/`, then `cook dub synth` on it (~10 min). Hand the wavs to the user and get an explicit OK on voice AND pace. The pilot doubles as the reference's rate measurement for Step 3's budget — one pilot, two jobs. Delivery pace is also tunable globally via the `DUB_DURATION_FACTOR` env (IndexTTS2 `duration_factor`; ~0.85 is a brisk pace, 1.0 neutral) — set it before synth; same value must have been behind any rate the budget used.

Done when `*.v1` backups exist (when merging ran), line count equals cue count post-merge, `<name>.zh.dub.srt` is regenerated, and the ear gate has an explicit user OK on voice AND pace.

### Step 4 — Synthesize the Chinese dub (the slow step)

```
cook dub synth <output-root> <name> --python <indextts-venv>/Scripts/python.exe
```

`stage_synth` loads IndexTTS2 once, then synthesizes each cue single-threaded (Step 0b; **[REFERENCE.md → "The single-thread constraint"](REFERENCE.md)**). Output is `dubbed/_full/_segments/sent_NNNN.wav`, cached by cue index — the cache is **NOT text-aware**: a cue whose text (or reference) changed re-synthesizes only after you delete its cached wav.

**Cost is per CUE, not per minute of video** (~3.5 min/cue regardless of length; 240 cues ≈ 14h). Quote the user `cues × 3.5 min` before starting. The synth log's completion line is `Stage 1 DONE: <n> cues synthesized`.

Done when `sent_NNNN.wav` exists for every cue AND each is > 1KB (not a truncated garbage file).

### Step 5 — Assemble on the identity timeline

```
cook dub assemble <output-root> <name> --python <indextts-venv>/Scripts/python.exe
# recovery after the post-burn quality gate edited dubbed/_full/ subtitle files:
cook dub assemble <output-root> <name> --python <indextts-venv>/Scripts/python.exe --keep-subs
```

One command, six moves (each logged with its `2a`-`2f` step letter):

- **Fit pass** — each cue's audio is atempo'd into its own window (cue start → next cue's start), in either direction; a factor near 1.0 is the norm because the translation was budgeted. A factor far from 1.0 logs a **budget-miss warning naming the cue** — the fix is editing that sentence and re-synthesizing that cue — never re-timing the video instead (why: **[REFERENCE.md → "The retired re-timing path"](REFERENCE.md)**).
- **Place** — cues at their original starts, silence in between; `dub.wav` comes out exactly the raw duration (asserted; the stage aborts rather than emit a different-length track).
- **Subtitles on the original clock** — ZH windows span the audio (cue start → max(cue end, audio end)); EN full sentences likewise; then the same shorten → merge-short → biliteral → ass pipeline as the bilingual release. The union's repetition is role-swapped: **EN repeats across consecutive ZH cues by design** — the mirror of the bilingual release, where ZH repeats across EN fragments.
- **Upload subtitles** — the merged ZH + EN SRTs copy to `cloud-srt/zh.dub.srt` + `en.dub.srt`.
- **Geometry** — the ASS coordinate system adapts to the frame: `PlayResX = W × 1080 / H`, real bar = `220 × H / 1080` px, so the bar starts exactly at the video's bottom edge with uniform glyph scaling on any frame size.
- **Encode** — the raw video stream untouched (identity), pad + burn, dub (+ `no_vocals` bed at -18dB **only when it really carries signal**, mean > -50dB), loudnorm to -18 LUFS. The dub track is normalized to house level, **not** matched to the source master — a quiet source (screencast mics are often -30s LUFS) must not drag the dub down to a whisper.

`--keep-subs` skips subtitle regeneration and reuses the on-disk files — the recovery path after a hand edit; the ASS is still rebuilt from the on-disk bilingual SRT.

Done when `cooked/<name>.dubbed.mp4` exists, its duration matches the raw ±0.5s (identity violated = error, not a variant), **and** the two gates below — the post-burn review and the pixel check — have both cleared.

**Post-burn quality gate — fan-out subagent review (mandatory).** What gets burned is the biliteral union; both languages ship as upload subtitles, so errors here are the most visible kind. Fan out a subagent reading `dubbed/_full/dubbing.bilingual.srt` end-to-end (every cue), checking:

1. **Split words** — a Chinese word or English term broken across two cues by `shorten` (each cue must read as a complete, self-contained thought).
2. **Adjacent duplicates** — the defect is a cue whose ZH **and** EN are both verbatim identical to the previous cue; one language repeating across the other's breakpoints is the union's design.
3. **EN text in the ZH slot** — when the ZH stream has a gap window, the union can backfill the ZH line with the EN text (a known union defect). Fix it **in the union product**: edit that line in `dubbing.bilingual.srt` (continue the previous ZH line across the window), rebuild only the ASS from the fixed SRT, re-run assemble with `--keep-subs`. Rerunning `biliteral` recreates the same defect — the generator, not the input, is wrong.
4. **Lost tails** — `shorten`'s long-cue splitting can silently drop a cue's tail fragment (the window goes bilingual-blank mid-sentence). Check the union's long ZH cues against `translations_dub.txt`: every source line's ending survives in the burned stream.

**Style parity + pixel check (with every burn).** Content gates read text; a burned video also carries layout. Extract a frame at a speaking timestamp and diff the video region against the raw frame at the same timestamp — **zero pixels above the bar may differ by more than 60** (grayscale; subtitle text lives only in the bar, re-encode noise stays under the threshold). An eyeball "looks fine" is not a check: a subtitle block rendered into the picture survived three content-gate reviews once. The mechanical form: decode both frames, compare the region above the bar, count pixels differing by more than 60 — anything above zero is a layout bug.

### Step 6 — Verify

Play the video (full play, or 5-6 spot-checks across it) and check:
- **Duration == raw** (Step 5's done criterion).
- **Audio in every cue** — no cue silent, no two cues overlapping (the stage asserts this, but spot-check the first minute and the last).
- **Subtitle readability** — no line overflowing the bar.

Then report to the user: the absolute path of `<name>.dubbed.mp4`, the reference clip used, and the cue count. Done when all three checks pass and the report (path / reference clip / cue count) has been given to the user.

## Reference

Details pushed out of this file because they're consulted on demand:

- **[REFERENCE.md](REFERENCE.md)** — the **char-budget filling rules** (what expansion material is legitimate, and the invented-content ban), the full **term-retention list**, IndexTTS2 install (single-thread constraint, the garbage-audio bug), the **v2.5 API differences** (silent garbage via `infer_v2`, `use_bf16`/`use_qwen_emo`, required `lang`), Demucs raw commands, the IndexTTS2 vs VoxCPM2 comparison, and the **retired re-timing path** (why per-segment video retiming was abandoned — archived in `deprecated/`).
