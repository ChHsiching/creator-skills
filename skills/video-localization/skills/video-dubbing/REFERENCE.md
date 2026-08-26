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

## Bi-directional re-timing — the math

### The ratio

For each cue:
```
ratio = chinese_TTS_duration / english_window_duration
```
- `ratio < 1`: Chinese is shorter. The video segment gets **sped up** (compressed) to match.
- `ratio > 1`: Chinese is longer. The video segment gets **slowed down** (stretched) to match.
- `ratio ≈ 1`: no change.

Normal-rate audio is **never** time-stretched or atempo'd — every cue plays at its natural TTS speed, and length mismatches are absorbed on the video side. Slow cues (the short-line pacing bug) are fixed per SKILL.md Step 4's speed-up ladder — the ladder's last rung is DSP `atempo` capped at 1.6x per cue, under the pacing policy, not a contradiction of it.

### The string-of-pearls timeline (overlap-proof)

Naive approaches overlap. If you place each cue at `original_start + front_padding` independently, cues that were close in the original (e.g. 0.14s gap) collide after re-timing (both expand into the same new-timeline region). The string-of-pearls construction is provably overlap-free:

1. Walk the cues in order. Maintain a running `new_clock`, starting at 0.
2. For each gap between cues: `new_clock += original_gap_duration`. (Gaps are preserved as-is — they carry the original rhythm.)
3. For each cue: `cue.new_start = new_clock`. `cue.new_end = new_clock + chinese_TTS_duration`. `new_clock = cue.new_end`.

Because `new_clock` only ever increases, and each cue's `new_end` becomes the next cue's `new_clock` baseline, **two cues cannot overlap by construction**. This is checkable: assert `cues[i].new_start >= cues[i-1].new_end` for all i.

### Why re-time video, not audio

The old approach (VoxCPM2 + atempo) stretched the audio to fit the window. Problems:
- atempo > 1.3x: chipmunk voice.
- atempo < 0.8x: drunken drawl.
- The ±25% cap meant long Chinese cues still didn't fit, producing alignment-issues.md files full of "this cue couldn't be stretched enough."

Re-timing the video instead:
- 1.2x video speedup is invisible on talking-head footage (viewers don't notice frame-dropping at 60fps source).
- 0.7x video slowdown is acceptable (the speaker moves a bit slower; with minterpolation it's smooth).
- Normal-rate audio stays untouched end to end — the only audio processing the pipeline ever does is the pacing policy's bounded per-cue speed-up of confirmed-slow cues.
- The only limit is how much speedup viewers tolerate before the picture looks fast-forwarded (>1.5x is the threshold).

### Expected duration change

A faithful Chinese translation is typically 10-30% longer or shorter than the English, depending on the content. Technical talks (lots of English terms retained) tend to run shorter (Chinese grammar is more compact). Storytelling content runs longer (Chinese needs more syllables for the same meaning). The re-timed video will be 10-30% off the original duration — this is expected and acceptable.

### timeline.json — schema

`dubbed/_full/timeline.json` is the plan every later stage (retime, burn, subtitles, adjuster) consumes. Top level: `{"timeline": [segments], "total_new": float, "raw_dur": float, "adjust": {...} (written by adjust_timeline.py)}`. Segment fields:

| field | kind | meaning |
|---|---|---|
| `kind` | cue/gap | `cue` = a spoken sentence (audio + video); `gap` = pause between cues (video only) |
| `idx` | cue | cue number — indexes `sent_<idx:04d>.wav`, translations_dub.txt line, en.full.srt cue |
| `orig_start`, `orig_end` | both | the segment's window on the RAW video clock |
| `zh_dur` | cue | the synthesized audio's exact duration (seconds) |
| `text` | cue | the ZH sentence (same as translations_dub line `idx`) |
| `en` | cue | the EN full sentence |
| `new_start`, `new_end`, `new_dur` | both | the segment's window on the re-timed clock; segments tile back-to-back (next.new_start == prev.new_end) |
| `speed` | both | orig_dur / new_dur playback rate (0.45x = slowed, 1.2x = sped up); gaps carry it too (1.0 unless an adjuster stretched them) |

Invariants to respect when writing tools that edit this file: segments tile contiguously; starts strictly monotonic; a cue's audio (`zh_dur` from its `new_start`) never overlaps the next cue's audio.

## minterpolate — parameter tuning and alternatives

### The chosen parameters

```
minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:me=epzs:vsbmc=1
```

- `mi_mode=mci` — motion-compensated interpolation (the only mode that actually generates new frames; `blend` just averages).
- `mc_mode=aobmc` — advanced overlapped block motion compensation (highest quality).
- `me_mode=bidir` — bidirectional motion estimation (uses both past and future frames).
- `me=epzs` — the motion estimation algorithm. `esa` is higher quality but 5-10x slower; `epzs` is the quality/speed sweet spot.
- `vsbmc=1` — variable-size block motion compensation (handles local motion better than fixed blocks).

### The hand-artifact limitation

Optical-flow interpolation fails on **fast non-rigid motion**. The classic case: a waving hand. The hand moves too fast for the flow estimator to track, so it produces two ghosted hands (the before and after positions averaged). This is architectural — no parameter tuning fixes it.

**Mitigations** (in order of preference):
1. **Accept it** — on talking-head videos (the common case), hands are in frame briefly and the artifact is tolerable. The user has accepted this trade-off.
2. **`mi_mode=blend`** — frame averaging produces a natural motion blur (like a camera shutter) instead of ghosting. Smoother-looking but less sharp. Use if the user objects to ghosting.
3. **No interpolation** — pure `setpts` slowdown. The segment plays at 15-40fps effective (choppy) but has zero artifacts. Use for action footage where ghosting is unacceptable.

Do **not** try `mc_mode=obmc` (lower quality than aobmc) or `vsbmc=0` (worse) thinking they reduce artifacts — they don't, they just reduce quality.

### Cost

Interpolated segments run at RTF ~23 on CPU. A typical 11-min video has ~90 slowed segments totaling ~7 min of output video — that's ~2.8 hours of processing. Combined with TTS (~8h at 141 cues), the full pipeline is ~11 hours on CPU. GPU (if available) cuts minterpolate to minutes but doesn't help IndexTTS2 (which is CPU-bound by the single-thread constraint).

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

The `cook dub mix` command auto-detects this — but if you're mixing manually, check first or you'll amplify silence.

## Chinese-dub quality self-check

After burning, listen for these failure modes:

- **洋腔 (foreign accent)** — the Chinese sounds like a non-native speaker. If severe, the reference audio was too English-heavy; try a different reference clip or switch engines. IndexTTS2 should have almost none.
- **Term-translation mismatch** — the dub says "快照" but the screen shows "snapshot." This means a clause-2 term (on-screen content) was wrongly translated. Audit the term list against the video.
- **Audio gaps** — silence where there should be speech. A cue failed to synthesize (check `dubbed/_full/_segments/` for < 1KB files) or the timeline placement is wrong (check `timeline.json` for `new_start > new_end`).
- **Subtitle overflow** — text clipped at screen edges. The `shorten --max-zh` is too high for the font size; re-run shorten with a lower limit (try 36, then 30).

## Fallback: 豆包 voice-clone 2.0 API

Kept in `scripts/doubao_synth.py` for cases where IndexTTS2 can't run (no CPU time, need speed). **Not recommended for Chinese dub** — cross-language cloning produces severe 洋腔. But it's 100x faster (API, RTF ~0.02) and works for prototyping.

API details in the script header. Key gotchas:
- Training uses `speaker_id: "custom_speaker_id"` + `custom_speaker_id: "<your name>"`.
- Synthesis uses `speaker: "<your name>"` + header `X-Api-Resource-Id: seed-icl-2.0`.
- Returns streaming JSON, one chunk per line, `data` field is base64 PCM.
- Use `audio_params.format: "pcm"` to avoid WAV header concatenation issues.
