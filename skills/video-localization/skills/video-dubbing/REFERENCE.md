# video-dubbing — REFERENCE

Load this when the situation calls for it. The SKILL.md is the primary tier; this holds what's consulted on demand.

## IndexTTS2 — install and the single-thread constraint

### Why IndexTTS2, not VoxCPM2 or 豆包 API

Tested three engines on the same 11-minute Matt Pocock video (English source, Chinese dub):

| Engine | 洋腔 (foreign accent) | Tail leakage | Install | Speed (CPU) | Verdict |
|---|---|---|---|---|---|
| **IndexTTS2** | almost none ("还行") | none | local clone + venv | RTF ~30-36 | **chosen** |
| VoxCPM2 (Ultimate Cloning) | severe ("像日本人发不出 r 音") | severe (continues into next sentence: "and...") | pip, heavy | RTF ~1-2 | rejected |
| 豆包 voice-clone 2.0 API | severe ("太垃圾了") | none | API key, fast | RTF ~0.02 (API) | rejected, code kept as fallback |

VoxCPM2's leakage is architectural — its continuation model naturally "keeps talking" after the input text, leaking the reference audio's next sentence. No post-processing fixes it. 豆包's accent comes from cross-language cloning: an English reference produces Chinese with English phonetic habits. IndexTTS2 (B站开源, large Chinese training corpus) avoids both.

### The single-thread constraint (load-bearing)

IndexTTS2 **must** run single-threaded. Multi-threaded inference produces 0.05s truncated garbage audio. Root cause: `SeamlessM4TFeatureExtrator`'s FFT has a float-reduction non-determinism under multi-threading (Issue #679). The fix:

```python
import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

import torch
torch.set_num_threads(1)
torch.set_num_interop_threads(1)

# NOW import indextts
from indextts.infer_v2_5 import IndexTTS2
```

**Order matters**: the env vars must be set before any numerical library imports. Setting them after torch loads has no effect. Every script in `scripts/` does this at the top.

Cost: RTF jumps from ~5 (multi-thread, broken) to ~30-36 (single-thread, correct). A 141-cue video takes ~8 hours on a Ryzen CPU (~3.5 min per cue — see SKILL.md Step 4 for the per-cue cost model). This is unavoidable — there is no "fast and correct" mode.

### Install

Upstream requires [uv](https://docs.astral.sh/uv/) for a reliable install (`pip install -U uv`); the full guide is the upstream README.

```bash
git clone https://github.com/index-tts/index-tts.git ~/Git/index-tts
cd ~/Git/index-tts
uv sync           # plain sync installs core inference; extras (deepspeed/flash-attn) are only guaranteed with a CUDA toolkit — see upstream README's Windows note
uv tool install "huggingface-hub"
hf download IndexTeam/IndexTTS-2.5 --local-dir=checkpoints   # ~5.2GB
```

Auxiliary models (w2v-bert-2.0 at ~4.4GB dominates, plus BigVGAN, CAMPPlus, MaskGCT) auto-download into `checkpoints/hf_cache/` on first run. Upgrading from v2 instead? Copy the old `checkpoints/hf_cache/` over — no re-download needed.

The dub pipeline also needs `demucs` (vocal separation) and `whisperx` (reference extraction) — neither is in upstream's lockfile:

```bash
uv pip install demucs whisperx
```

A later `uv sync` prunes them again (`uv sync` is exact) — and so does any `uv run` in this repo, which exact-syncs implicitly (narrate-video's launches do). Reinstall after re-syncing.

Verify the venv resolves the v2.5 module:
```bash
.venv/Scripts/python -c "from indextts.infer_v2_5 import IndexTTS2; import demucs, whisperx; print('OK')"
```

### v2.5 API — the differences that break v2.0 code

Loading v2.5 checkpoints through the old `infer_v2` module produces garbage audio with **no error** — the failure is silent. Every synth script in this skill therefore uses:

- `from indextts.infer_v2_5 import IndexTTS2` (not `infer_v2`)
- init: `use_bf16=` replaces `use_fp16=`; `use_qwen_emo=False` skips the emotion model — only `use_emo_text=True` needs it, and that hard-requires `use_qwen_emo=True` at init (RuntimeError otherwise)
- `infer(...)` takes a required `lang` argument (`"zh"` for this pipeline; case-insensitive)
- output WAVs are properly scaled now — the old install clipped every output to 0dBFS (fixed upstream in #773); peaks vary per cue (measured -2 to -5dBFS), with no internal loudness normalization. A `_segments/` cache from a pre-upgrade run mixes 0dBFS v2.0-era cues with quieter v2.5 cues — delete it when resuming.
- v2.5 tokenizes via tiktoken; `infer_v2_5` never reads `bpe.model` (the file still ships in the checkpoint download)

### Reference audio requirements

- **14-30 seconds** of clean continuous speech (no silence gaps > 0.3s).
- 16kHz mono WAV.
- Extracted from Demucs-separated `vocals.wav` (not the raw mix — BGM contaminates the clone).
- Longer than VoxCPM2's 8s because IndexTTS2 clones prosody (rhythm + intonation), which needs more material than timbre-only cloning.
- No post-processing needed — IndexTTS2 output has no tail leakage and no trailing noise.

## Term retention list

Which English terms stay English in the Chinese dub, and which become Chinese. The rule has two clauses:

### Clause 1: Developer-community terms stay English

These are how Chinese developers actually say them — translating to Chinese sounds artificial:

`spec` `plan` `Plan mode` `spec-driven` `prototype` `Wayfinder` `grilling` `grilling skill` `grilling session` `agent` `AFK agent` `skill` `skills` `skills newsletter` `token` `compact` `QA` `ship` `production` `session` `planning session` `prototype session` `UI` `UI prototype` `ticket` `ticket types` `asset` `artifact` `stub` `branch` `throwaway branch` `throwaway route` `route` `live` `live route` `filter` `design tree` `design tools` `clear` `handoff` `reference docs` `fidelity` `state machine` `state model` `design decision` `case` `app` `copy and paste` `AI` `Agile` `Shape Up` `Ryan Singer` `tldraw` `canvas` `wireframe` `spike` `throwaway spike` `diagram` (abstract concept noun)

### Clause 2: On-screen content stays English (regardless of clause 1)

If the speaker references something **visible in the video** — a search term they type, a UI label, code on screen, a filename — keep it in English even if it has a standard Chinese name. The viewer sees the English on screen; the subtitle must match or they'll be confused.

Examples from the Matt Pocock video:
- **`current`** — Matt points at a UI option labeled "current" and says "I don't like these current things." Translate to 当前 and the viewer can't find what he's pointing at. **Keep `current`.**
- **`model`** — Matt types "model" into a search box (visible) and says "let's search for model again." Translate to 模型 and the search box still shows "model." **Keep `model`.**
- **`search diagrams`** — a UI element literally labeled "search diagrams" at the top of the screen. **Keep `search diagrams`.**

The test: pause the video at that cue. Is there English text on screen that the speaker is referring to? If yes, keep it. If the term is only spoken (no on-screen text), apply clause 1.

### Concepts with standard Chinese names → translate

When a term has a common Chinese name AND isn't shown on screen, translate it:

| English | Chinese | Why |
|---|---|---|
| snapshot | 快照 | standard in DB/version-control contexts |
| picker | 选择器 | standard UI term |
| option | 选项 | standard UI term |
| search box | 搜索框 | standard UI term |
| data model | 数据模型 | standard technical term |
| front-end | 前端 | universally used in Chinese |
| back-end | 后端 | universally used in Chinese |

When unsure, ask the user with context — "this term appears at timestamp X, here's the sentence, keep English or translate?"

## Demucs — raw commands (fallback when `cook dub separate` is missing)

```bash
python -m demucs --two-stems=vocals --name htdemucs -o <output-root>/dubbed/ \
    <output-root>/raw/<name>.raw.mp4
```

Use `htdemucs` (single model, ~3GB RAM). Do **not** use `htdemucs_ft` (bag of 4 models, ~20GB RAM — OOMs on 32GB machines). The `_ft` variant's quality advantage is irrelevant here — we only need clean enough vocals to extract a reference clip.

## Background music — detect before mixing

Not every video has BGM. Test `no_vocals.wav`'s RMS before mixing:

```bash
ffmpeg -i no_vocals.wav -af volumedetect -f null - 2>&1 | grep mean_volume
```

- **mean_volume < -50dB**: no BGM (pure talk video). Replace vocals entirely — don't mix. The Matt Pocock test video measured -60dB.
- **mean_volume > -50dB**: BGM present. Mix `dub.wav` (full volume) + `no_vocals.wav` (ducked to -18dB) so the BGM is present in silence but the dub wins when the speaker talks.

The assemble stage auto-detects this (mean > -50dB mixes a -18dB bed under the dub); check first if you're mixing manually, or you'll amplify silence.

## Chinese-dub quality self-check

After burning, listen for these failure modes:

- **洋腔 (foreign accent)** — the Chinese sounds like a non-native speaker. If severe, the reference audio was too English-heavy; try a different reference clip or switch engines. IndexTTS2 should have almost none.
- **Term-translation mismatch** — the dub says "快照" but the screen shows "snapshot." This means a clause-2 term (on-screen content) was wrongly translated. Audit the term list against the video.
- **Audio gaps** — silence where there should be speech. A cue failed to synthesize (check `dubbed/_full/_segments/` for < 1KB files) or the placement is wrong (the assemble stage already asserts dub.wav total = raw duration and per-cue windows — re-run it with the log visible).
- **Subtitle overflow** — text clipped at screen edges. The `shorten --max-zh` is too high for the font size; hand-edit the merged SRT and re-run `cook dub assemble --keep-subs` (shorten runs inside assemble with a fixed limit; there is no standalone re-run).

## Fallback: 豆包 voice-clone 2.0 API

For cases where IndexTTS2 can't run (no CPU time, need speed); the original helper script is not shipped with this skill. **Not recommended for Chinese dub** — cross-language cloning produces severe 洋腔. But it's 100x faster (API, RTF ~0.02) and works for prototyping.

API details in the script header. Key gotchas:
- Training uses `speaker_id: "custom_speaker_id"` + `custom_speaker_id: "<your name>"`.
- Synthesis uses `speaker: "<your name>"` + header `X-Api-Resource-Id: seed-icl-2.0`.
- Returns streaming JSON, one chunk per line, `data` field is base64 PCM.
- Use `audio_params.format: "pcm"` to avoid WAV header concatenation issues.

## Filling the char budget

Legitimate fill material for a cue's char budget (Step 3), in priority order:

1. **English detail the subtitle-style pass compressed away.** Restored
   clauses, spelled-out implications, the speaker's own restatements. Read the
   EN cue against your line and put back what meaning was dropped.
2. **Speaker-style discourse markers.** 「什么意思呢」「为什么这么说」「你会看到」
   「对吧」 — the connective tissue a speaker actually says. Rotate them: the
   same marker twice in a script is noticeable, five times is a defect (a
   10-occurrence collision shipped once from three parallel expanders).

**After parallel filling** (several writers or subagents each filled budgets):
grep every discourse marker and cap each at 1-2 uses — collisions are the
signature failure of multi-writer expansion.
3. **Unpacked compressions.** 「物化记忆」→「一种物化下来的记忆」; a
   glossed compound becomes the full phrase it stands for.

**Never**: new facts, new numbers, new analogies, invented attributions
("this is my personal experience" when the speaker said nothing of the sort),
or comforting narration the speaker never uttered. The dub says what the
speaker said — at speaking length.

## Editing the dub script

Change lines with exact-match replacements (a script that asserts the old
text is present before replacing it), never whole-file rewrites — a rewrite
has twice shipped with accidental line breaks that broke cue alignment.

## The retired re-timing path (archived)

The original pipeline re-timed each video segment to the Chinese audio
(speed-up drops frames; slow-down `setpts` + `minterpolate` at 60fps). On
long content it failed the ear check — a 74-minute dub with 600+ interpolated
segments played "like dropped frames". The identity timeline replaced it:
video untouched, per-cue audio atempo into original windows. The identity
timeline is the only supported path; the archive in `deprecated/` (code
snapshot, adjuster, rate report, reference sections, tests) is read-only.


## Rate recalibration (when the reference or duration factor changes)

The char budget is only as good as the speech rate behind it. A budget
calibrated to one reference clip silently mis-fits after swapping in another
(faster or slower) clip or changing `DUB_DURATION_FACTOR` — every line-level
gate passes, and the dub lands as dead air or compression. Recalibrate before
trusting an existing script against a new voice:

1. **Stratified probe.** Pick 5-10 existing script lines per speaker across
   length bands (roughly 15-25, 30-45, 50+ chars — the bands behave
   differently). Synthesize each with the new reference + df (the production
   worker config, not a one-off).
2. **Measure per band**, CJK-equivalent syllables per second: a CJK char is
   one syllable; an English word counts its vowel groups; a digit run counts
   its digits. Observed on IndexTTS2 clones: ~15-25-char lines 4-5 syll/s,
   ~30-50-char lines 5.5-6.5, chunked long cues 6-7; very short lines (<=8
   syllables) drop to 2.6-3.0 (the short-line trap — never calibrate from
   them).
3. **Re-check the script** against `window x band-rate` per cue, the same
   arithmetic the length gate does, with the measured rates in place of its
   generic planning bands. Lines under ~88% of their window budget need
   expansion (see "Filling the char budget"); lines over ~105% need cuts.
4. The generic bands baked into `length_gate.py` (3.0/4.2/4.9) are planning
   defaults, not physics — measured rates from the actual voice override them.

## IndexTTS2 sampling — the live knobs

- `use_random` only acts on the emotion-vector path (`emo_vector is not None`).
  In the pure-clone configuration (no `use_qwen_emo`, no `use_emo_text`,
  no explicit `emo_vector`) it is a **no-op** — flat prosody there is the
  reference window's fault, not the sampler's. The window's own prosody IS
  the emotion conditioning in pure clone: a flat window dubs flat.
- `temperature` / `top_k` / `top_p` (defaults 0.8 / 30 / 0.8) pass through
  infer's `**generation_kwargs` and are the live sampling knobs. Two takes of
  the same sentence at default settings differ audibly (measured F0 std 25.9
  vs 21.6) — the per-take lottery is alive without `use_random`. A slightly
  raised temperature (1.0) livened one voice while cleaning its ASR
  round-trip; raise with care, garble risk rises with it.
- One reference file per md5 has bitten three rounds: before blaming the
  voice, md5 the ref chain (`ref.wav`, `ref_<S>.wav`, every copy) and confirm
  they are the file you think they are.

## Reference authentication — derivatives fool waveform correlation

A reprocessed derivative of a speaker's real audio (resampled, re-encoded,
loudness-processed) keeps the speaker embedding and the pitch statistics but
loses waveform correlation. Testing "is this the same recording?" with
waveform correlation therefore produces false negatives (a real round
concluded "not the same voice" from correlation -0.05; the file scored 0.9438
speaker-embedding cosine against a same-speaker anchor and its pyin stats
matched the source window almost exactly). To authenticate a reference file:

- `scan_reference.py --score <file> --anchor <real-clip-of-the-speaker>` —
  same-speaker real audio lands near 0.94; synthesized takes 0.66-0.76.
- pyin F0 median/std/range vs the claimed source window (resampling moves
  them little; heavy processing flattens std).
- Derivative or not: a degraded source clones its degradation. Cut fresh from
  the clean source (16 kHz mono `pcm_s16le` from the original) rather than
  rehabilitating a processed file.

## Editing the burned bilingual SRT (union product)

The biliteral union is regenerated by every plain assemble — hand edits land
in `dubbed/_full/dubbing.bilingual.srt` and survive only via
`cook dub assemble --keep-subs`. Two traps when editing it:

- **Repeated fragments need replace-ALL.** shorten splits long EN sentences
  into fragments that repeat across consecutive cues; a `count=1` replace
  hits the first occurrence, which may be a different cue than the one you
  are fixing. Assert uniqueness before single replaces.
- **Cross-cue text edits are block-based.** The two ZH lines of adjacent cues
  are NOT adjacent lines in the file (the EN line and the next cue's header
  sit between them) — a line-adjacency replace never matches. Split into
  blocks, edit the block's line, rejoin.

Defect classes worth scanning after every assemble (each shipped at least
once): split words at cue boundaries including number-unit splits
("两千五百个 | PR", "2000 | PRs") and determiner-noun splits ("那些 |
东西"); a cue whose ZH is a strict prefix-extension of the previous cue's ZH
(the stutter — restart-and-extend; an equal repeat is the union's design);
half-dash pairs ("—|—" split across cues); EN text in the ZH slot; lost
source-line tails. Single-language repetition across the other language's
breakpoints is the union working as designed — flag it and you will be
correcting the design, not a defect.

## Last-cue window — derive it, never assume it

The last cue's window runs from its start to the END OF THE VIDEO, which can
be seconds (a stream that hard-cuts right after the final line) — not "some
default window". `full_dub.cue_window` derives it from the raw duration; any
ad-hoc script that recomputes windows (budget checkers, expansion
worklists) must do the same from the ffprobe duration. A hardcoded fallback
constant produced a 5x-overwindow closing line that had to be rewritten and
re-synthesized on the spot.
