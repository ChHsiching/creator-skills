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
from indextts.infer_v2 import IndexTTS2
```

**Order matters**: the env vars must be set before any numerical library imports. Setting them after torch loads has no effect. Every script in `scripts/` does this at the top.

Cost: RTF jumps from ~5 (multi-thread, broken) to ~30-36 (single-thread, correct). A 141-cue video takes ~7 hours on a Ryzen CPU. This is unavoidable — there is no "fast and correct" mode.

### Install

```bash
git clone https://github.com/index-tts/index-tts.git ~/Git/index-tts
cd ~/Git/index-tts
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
# models land in checkpoints/ — first inference downloads them (~3GB)
```

Verify single-thread inference works:
```bash
.venv/Scripts/python -c "import os; os.environ['OMP_NUM_THREADS']='1'; import torch; torch.set_num_threads(1); from indextts.infer_v2 import IndexTTS2; print('OK')"
```

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

The Chinese audio is **never** atempo-stretched. Every cue plays at its natural TTS speed.

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
- No audio artifacts ever — the TTS output is sacred.
- The only limit is how much speedup viewers tolerate before the picture looks fast-forwarded (>1.5x is the threshold).

### Expected duration change

A faithful Chinese translation is typically 10-30% longer or shorter than the English, depending on the content. Technical talks (lots of English terms retained) tend to run shorter (Chinese grammar is more compact). Storytelling content runs longer (Chinese needs more syllables for the same meaning). The re-timed video will be 10-30% off the original duration — this is expected and acceptable.

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

Interpolated segments run at RTF ~23 on CPU. A typical 11-min video has ~90 slowed segments totaling ~7 min of output video — that's ~2.8 hours of processing. Combined with TTS (~7h), the full pipeline is ~10 hours on CPU. GPU (if available) cuts minterpolate to minutes but doesn't help IndexTTS2 (which is CPU-bound by the single-thread constraint).

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
- **Audio gaps** — silence where there should be speech. A cue failed to synthesize (check `_segments/` for < 1KB files) or the timeline placement is wrong (check `timeline.json` for `new_start > new_end`).
- **Subtitle overflow** — text clipped at screen edges. The `shorten --max-zh` is too high for the font size; re-run shorten with a lower limit (try 36, then 30).

## Fallback: 豆包 voice-clone 2.0 API

Kept in `scripts/doubao_synth.py` for cases where IndexTTS2 can't run (no CPU time, need speed). **Not recommended for Chinese dub** — cross-language cloning produces severe 洋腔. But it's 100x faster (API, RTF ~0.02) and works for prototyping.

API details in the script header. Key gotchas:
- Training uses `speaker_id: "custom_speaker_id"` + `custom_speaker_id: "<your name>"`.
- Synthesis uses `speaker: "<your name>"` + header `X-Api-Resource-Id: seed-icl-2.0`.
- Returns streaming JSON, one chunk per line, `data` field is base64 PCM.
- Use `audio_params.format: "pcm"` to avoid WAV header concatenation issues.
