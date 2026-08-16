---
name: tts-forge
description: Provider-agnostic voiceover production. Use when a video has no audio track and needs a voice, when the user mentions 配音 / voiceover (TTS), when a voice must be chosen or swapped, or when another skill (e.g. a video router) hands off a voiceover task. For adding narration plus burned-in subtitles to an already-finished video, narrate-video is the entry point — it runs its own IndexTTS2 voice pipeline. Covers MiniMax (mmx-cli) and OpenAI built-in; any other provider via a small wrapper you write.
---

# tts-forge

Turn display text into a narrated audio track: choose a provider, choose a voice by ear, then synthesize without burning money twice.

## Step 1 — Choose the provider with the user

Present the trade, let them pick:

| Route | Best at | Cost model | Setup |
|---|---|---|---|
| MiniMax (`mmx-cli`) | Chinese narration, natural prosody | ~¥0.2-0.35 / 1k chars (list price — verify at platform.minimaxi.com) | `mmx` CLI + login (`--region=cn`) |
| OpenAI TTS | quick start, most agents already hold a key | per-char, cheap | `OPENAI_API_KEY` |
| edge-tts | free, offline-ish drafts | free | local binary |
| ElevenLabs / Azure / Google | premium English/brand voices | subscription | provider portal |

Two provider-specific traps worth stating to the user up front: MiniMax authentication is not enough — the account needs balance topped up; and the default MiniMax voice is unpleasant enough that voice selection (Step 2) is mandatory.

After the user picks, collect the credential (API key / login) before any synthesis attempt, and store it where the run's scripts expect it (env var or CLI session).

Done when: provider chosen and credential stored where the run's scripts read it.

## Step 2 — Audition voices before spending

Audition on the provider's free channel before any paid synthesis:

- MiniMax: the voice library page (minimaxi.com/audio/voices) previews every voice free — pick there, then bring the voice ID here.
- OpenAI: synthesize one short line per candidate voice (a few cents total) and play them for the user.

The user picks the voice. Record the voice ID in the run notes — every later synthesis command takes it explicitly.

Done when: the user has picked a voice and its ID is in the run notes.

## Step 3 — Spoken script vs display text

One script, two renderings:

- **Narration script** (what TTS reads): homophones disambiguated, symbols spelled out, numbers written as spoken digits, no code tokens. Multi-pronunciation characters and English identifiers inside Chinese text are the top failure sources — rewrite each into how it should be *said*.
- **Display text** (what the viewer reads): exact terms, code, punctuation preserved.

Skipping the split produces mispronounced product names and comically read-out symbols. Write both, show the user the narration script, get a nod, then synthesize.

Done when: the user has approved the narration script.

## Step 4 — Synthesize incrementally

Run `scripts/synthesize.sh <segments.tsv> <out-dir> --provider <p> --voice <id>` — it loops segments serially with skip-existing resume, reports per-run cost, assembles `narration.mp3`, and its `--force` flag states the full re-spend cost before invalidating a voice change. The TSV carries `id	text` per segment.

## Provider quick reference

Any provider beyond the built-ins (ElevenLabs, edge-tts, Azure, Google) becomes one small wrapper exposing the same three commands: audition, synthesize-segment, skip-existing.

Done when: the script reports `SYNTH_DONE` with zero failed segments and `narration.mp3` plays every segment end-to-end.