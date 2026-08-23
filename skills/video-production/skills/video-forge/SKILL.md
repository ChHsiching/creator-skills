---
name: video-forge
description: Turn source material — a URL, article, image set, podcast, or video file — into a finished, publishable video. Use when the user provides material and wants it turned into a video (做视频 / 视频化 / 可视化), or asks what turning content into a video involves. If the user explicitly invokes remotion-video-director by name, or wants from-scratch motion design with no source material, defer to it and skip this skill.
---

# video-forge

You are the **router** that turns source material into a finished video. The creative build belongs to `remotion-video-director`; your job is everything upstream (material, intake, gates) and downstream (render strategy, covers, platform variants, publish copy) of it.

```
material → ingest → intake interview → build-ready gates → director handoff → delivery
```

## The scope/shape boundary

Every decision in this pipeline belongs to exactly one side:

- **Scope is yours** — which part of the material becomes the video: full length vs highlights vs full-plus-clips, subtitle language, the visualization form the material supports, audience wording level, platform targets. `remotion-video-director` assumes the video's shape is already decided when it starts.
- **Shape is the director's** — creative direction, pacing, music, look, scene design: how the decided scope is executed. It asks these itself; pre-asking them in your interview steals its job and bores the user with duplicate questions.

If the director probes scope anyway (e.g. duration constraints), answer from intake — never re-ask the user.

## Step 0 — Probe dependencies

Check these skills are discoverable (by their descriptions being present):

- `remotion-video-director` — required. Without it, stop and give the install command: `npx skills add <owner>/remotion-video-director` (the README install section carries the current owner).
- `remotion-4k-polish` — required before any 4K final render. Point the user to install if missing.
- `tts-forge` — required only when material has no audio track and the user wants voiceover.
- `no-ai-slop` (github.com/petergyang/no-ai-slop) — powers the AI-flavor gate's pattern axis (Step 3). Install: `npx skills add https://github.com/petergyang/no-ai-slop --skill no-ai-slop`. When missing, the gate falls back to the inline pattern list in materials.md.

Tools (binaries, not skills — probe like ffmpeg): the `cook` CLI is the transcription executor for AV material. Resolve its shared environment and upgrade it before first use (protocol in `references/materials.md` — "Transcription environment"); without it, fall back to whisperx directly (works, but you hand-roll detach/log-polling).

Done when: remotion-video-director is discoverable (or its install command was given), 4K/tts and no-ai-slop availability are known (or the inline fallback is chosen), and for AV material the cook CLI is present (or the whisperx fallback is chosen).

## Step 1 — Ingest material

Dispatch by what the user handed you, then read `references/materials.md` before processing:

| Material | Dispatch |
|---|---|
| Audio / video file | transcription pipeline |
| URL (page / article / post) | fetch pipeline |
| Images | asset inventory (processing per materials.md) |

Done when: a usable content source exists on disk (transcript, article text, or asset inventory) plus source metadata (author, URL, title — where the source has any) for attribution.

## Step 2 — Intake interview

Six categories, wording adapted to the material, asked through the host's structured question tool with previews for form options: scope, subtitles, form, audience/red lines, platform & specs, voiceover (silent material only — settles the **timing authority** too, audio-first by default; hands off to tts-forge).

Read `references/intake.md` before interviewing — it carries the per-category questions, the form-derivation rule, and the **director brief** format. Done when: every category has an answer the user gave or explicitly defaulted.

## Step 3 — Material to build-ready

Three gates between raw material and the director handoff — **terminology**, **AI-flavor**, **fact verification** — with their protocols single-homed in `references/materials.md`. Scale to the material: a 10-cue short needs one full pass per gate, not subagent loops.

Read `references/materials.md` for the gate protocols. Done when: every gate has a zero-defect pass and timestamps still match the source byte-for-byte.

## Step 4 — Director handoff

Assemble the director brief — the single artifact that carries everything intake and the gates produced. Its format is in `references/intake.md`. Then load `remotion-video-director` and hand it the brief as pre-answered Phase 1 discovery — it still runs its own Creative Direction and Creative Brief steps (the shape questions), flowing into Phase 2 and beyond. Stay available to answer scope-derived questions from intake answers.

Done when: every brief field in the intake.md format is filled from intake and gate outputs, and remotion-video-director has entered Phase 2 with it.

## Step 5 — Delivery

These are defaults you do, not questions you ask. Delivery runs as **four named gates in order — the run does not advance past a gate until it clears** (fix, then re-run the full gate; spot-checking the fixed item is not a pass). Each gate's exact checks live in `references/delivery.md` — read it before delivering.

- **G1 — stills approval**: every distinct layout/asset state as a labeled stills sheet; the user approves content and assets.
- **G2 — cheap full render with audio** (1080p; 540p for long videos): spec check passes (ffprobe vs intake answers), then the user approves content and timing.
- **G3 — content gates on the cheap render**: audio mix within loudness targets (ebur128 three-window), blank-scene sweep clean (85%-frame pixel diff), neutral-vision reads clean. All zero-defect.
- **G4 — final render + artifacts**: 4K render (read `remotion-4k-polish` first; long videos: `scripts/render_segments.sh`), every platform variant rendered and spec-checked, covers verified per ratio, publish copy complete and length-checked, ending spot-checked, output directory holds deliverables only.

Done when: G1–G4 have each cleared in order, ffprobe specs match the intake answers, and the ending frames of every variant have been spot-checked.

## Bundled scripts

Deterministic helpers under `scripts/` — run them instead of re-deriving the code (each bakes in a debugged-once pitfall):

- `scripts/srt_to_json.py` — SRT → Remotion subtitle JSON (bilingual split + count/first/last verification)
- `scripts/render_segments.sh` — segmented parallel render driver: resume, stagger, retry, integrity gate before concat
- `scripts/check_segments.sh` — post-kill moov/duration audit for any segment directory
