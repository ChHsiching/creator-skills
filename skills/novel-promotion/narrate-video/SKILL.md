---
name: narrate-video
description: Use when the user wants to add AI narration and burned-in subtitles to a finished silent video — mentions 旁白/配音/字幕烧录/narrate-video, hands over a video plus a script, or another skill hands off "video is done, add narration."
---

# narrate-video

**Narrate** a finished silent video: synthesize sentence-level voiceover with IndexTTS2, generate subtitles whose line breaks respect Chinese semantics, review those breaks, then burn voice + subtitles into the video. Input is a script file (used verbatim) and a silent video. Output is `final.mp4`.

The skill narrates videos it's handed — it does not generate the source video, write the script, or publish the result. Those belong to sibling skills orchestrated by a future router.

## The contract — one video per subdirectory

The user works in a **workspace directory**. Each video lives in its own subdirectory. narrate-video operates on one subdirectory at a time.

```
<workspace>/                          ← user's project root
├── <video-name>/                     ← one video's subdirectory
│   ├── script.txt                    ← required input: narration script
│   ├── video.mp4                     ← required input: silent source video
│   └── output/                       ← created by this skill
│       ├── _segments/                ← per-sentence TTS audio (cacheable)
│       ├── audio.wav                 ← final narration audio
│       ├── audio.srt                 ← sentence-level subtitles (verbatim)
│       ├── subtitle.ass              ← styled subtitle file (post-review)
│       └── final.mp4                 ← final product: video + voice + subs
```

**Done** means `<video-name>/output/final.mp4` exists, plays, has synced narration and readable burned-in subtitles.

## Step 0 — Resolve paths and inputs

Ask the user for the **video subdirectory path** if not given. Then verify its contents:

1. A script (`.txt` preferred). The user may also paste the script text directly — in that case, write it to `<subdir>/script.txt` for them. If multiple `.txt` files or none, ask which one.
2. A silent video (`.mp4` preferred). If multiple video files or none, ask which one.

If either is missing, stop and tell the user exactly what's missing and where to put it. **Done when** you can name the absolute paths of `script_path` and `video_path`.

## Step 1 — Resolve the IndexTTS2 installation

IndexTTS2 is a heavy install (~4 GB) and not shipped with this skill. The skill reuses an existing install — like the `video-subtitle` skill's venv-reuse approach: **probe, never persist a custom config file into the user's home directory.** The skill writes no dotfiles anywhere global.

Check these candidates in order, use the first whose `checkpoints/config.yaml` exists:

1. The `NARRATE_INDEXTTS_DIR` environment variable
2. `<workspace>/index-tts` (sibling of the video subdirectory's parent — common if the user keeps a single install next to their project)
3. Common locations under the user's home: `~/Git/novel-promotion/index-tts`, `~/index-tts`, `~/Documents/index-tts`

If none is found, ask the user: "IndexTTS2 在哪？给我它的安装目录（里面应该有 checkpoints/ 文件夹）。" Hold the answer in memory for the rest of this run only — do not write it to a file. (If the user wants to skip the question on future runs, they set `NARRATE_INDEXTTS_DIR` themselves — the skill never touches their shell config either.)

Also resolve `uv`: run `uv --version`. If missing, install it (`powershell -c "irm https://astral.sh/uv/install.ps1 | iex"` on Windows; the curl one-liner on macOS/Linux).

**Done when** you can name a directory containing `checkpoints/config.yaml` and `uv --version` works.

## Step 2 — Configure the narration voice, speed, and emotion

Three knobs shape the narration: the reference voice (IndexTTS2 clones it), the playback speed, and the emotion intensity. Configure all three together — this is one decision the user makes once per project.

**Reference voice** — the skill ships a default `voices/yunxi-male-fast.mp3` (young male, slightly fast, suited for novel narration). Offer:

- The default yunxi voice (recommended)
- Any other `.mp3`/`.wav` files in the skill's `voices/` folder
- A custom path the user provides

**Speed and emotion** — ask with `AskUserQuestion`, and let the user *hear* the difference before deciding. Generate one sample (the script's first sentence) at each candidate setting first so the user can compare. CPU synthesis is ~30s per sample, so three speed candidates is ~90s total — tell the user to expect that wait. Offer at minimum:

- **Speed**: 1.0× (原速), 1.15× (稍快，推荐), 1.3× (快), or a custom value the user types
- **Emotion intensity** (`emo-alpha`): 0.3 (轻度), 0.6 (中度，推荐), 1.0 (强烈), or custom

**Done when** the user has confirmed `ref_voice`, `tempo`, and `emo_alpha`. The skill does not persist these to a dotfile — each run asks, since different videos may want different settings.

## Step 3 — Generate sentence-level narration

This is the slow step (~4 minutes per 30s of narration on CPU). It will exceed the ~10-minute shell timeout of some agent environments for longer scripts, so **launch it detached and monitor**, never run it in the foreground.

**Resolve script paths** before invoking:

- `<skill>` = the absolute path to this skill's folder (where `SKILL.md` lives). The skill's `scripts/` and `voices/` are relative to it.
- `<indextts-dir>` = the directory resolved in Step 1.

### Windows — launch detached with PowerShell

Copy the skill's `scripts/windows-detached.ps1` template into `<video-subdir>/scripts/`, fill the five path variables, and run it. The template launches `uv run python gen_audio.py` via `Start-Process` so it survives the shell timeout:

```bash
powershell -ExecutionPolicy Bypass -File <video-subdir>/scripts/windows-detached.ps1
```

The launch returns immediately. Monitor with `Get-Process python` from PowerShell and tail `<video-subdir>/output/_segments/gen_audio.log`.

### macOS / Linux — launch detached with nohup

```bash
cd <indextts-dir>
PYTHONPATH="<indextts-dir>" nohup uv run python <skill>/scripts/gen_audio.py \
  <video-subdir>/script.txt \
  <ref-voice> \
  <video-subdir>/output \
  --tempo <tempo> \
  --emo-alpha <emo-alpha> \
  --indextts-dir <indextts-dir> \
  > <video-subdir>/output/_segments/gen_audio.log 2>&1 &
```

### After either launch

Sleep 15s, then confirm the log file has output and the process is still alive (`Get-Process python` on Windows; `ps aux | grep python` elsewhere). That's enough — a process alive with a growing log at 15s outlives the shell timeout.

The script caches per-sentence audio in `output/_segments/`, so re-runs after a parameter change only re-synthesize what changed.

**Done when** `<video-subdir>/output/audio.wav` and `<video-subdir>/output/audio.srt` both exist and `audio.srt` has exactly one cue per full sentence in the script (count them).

## Step 4 — Generate the subtitle display splits

Run `burn_subtitle.py` to apply the three splitting rules and produce a styled `.ass`:

```bash
uv run python <skill>/scripts/burn_subtitle.py \
  <video-subdir>/output/audio.srt \
  <video-subdir>/output/subtitle.ass
```

The three rules (applied per sentence, since the SRT has one cue per sentence):

1. **Short sentence** (fits on one line, ≤ 11 chars): show as-is.
2. **Long sentence without internal punctuation**: jieba semantic split into multiple visual lines.
3. **Long sentence with internal punctuation** (，；：): split at the punctuation first; any fragment that still overflows the screen gets jieba semantic split applied to it alone.

Subtitle text is **always verbatim** — no punctuation added, removed, or moved. Only `\\N` line breaks are inserted.

**Done when** `<video-subdir>/output/subtitle.ass` exists and every Dialogue line is ≤ 11 chars per visual line.

## Step 5 — Review the subtitle line breaks (mandatory)

This is the quality gate. jieba mis-segments proper nouns (兰若寺 → 兰若 + 寺), fixed collocations, and place names — including fragments produced by rule 3's per-fragment split. The agent **must** review every Dialogue line before burning.

**How to review**: read the ASS file's `Dialogue:` lines. For each, check the `\\N` break points against these rules:

- **No proper noun split** — 兰若寺, 宁采臣, 聂小倩, place names, book titles must stay whole on one line.
- **No particle stranded** — 的/了/着/在/上/下 never starts a line.
- **No line over 11 chars** — anything longer overflows the screen.
- **Breaks at semantic boundaries** — subject-predicate or verb-object, not mid-phrase.
- **Subtitle text is verbatim** — no characters added or removed vs. the script.

**Subagent pattern (for long scripts)**: if the script has many sentences, dispatch multiple subagents in parallel — each reviews a slice of the Dialogue lines and returns a list of `(line_number, current_break, suggested_fix)` tuples. They do **not** edit the file. The main agent collects all reports and applies the edits in one pass (avoids concurrent-write conflicts).

For the typical short narrate-video script (≤ 20 sentences), review inline — no subagent needed.

**Done when** every Dialogue line passes all five checks above. Edit the ASS in place to fix any failure.

## Step 6 — Burn subtitles into the video

Copy the reviewed ASS next to the video, then burn with ffmpeg. Run from the video subdirectory so the `ass=` filter receives a relative filename (Windows parses `C:` in filter args as an option separator — absolute paths break the filter).

```bash
cd <video-subdir>
cp output/subtitle.ass ./subtitle.ass
ffmpeg -y -i video.mp4 \
  -vf "ass=subtitle.ass" \
  -c:v libx264 -preset faster -crf 20 -pix_fmt yuv420p \
  -c:a copy \
  -movflags +faststart \
  output/final.mp4
```

For long videos (15+ minutes), launch ffmpeg detached using the same pattern as Step 3 to avoid the shell timeout. Never chunk or segment the encode — burn in one pass or subtitle timestamps drift.

**Done when** `<video-subdir>/output/final.mp4` exists, is non-empty, and a spot-check frame at a speaking timestamp shows the subtitle text rendered.

## Step 7 — Report

Tell the user:

- The absolute path of `final.mp4`
- Total duration and file size
- Sentence count, narration voice used, speed, emotion intensity
- Any subtitle breaks the agent corrected during review

Nothing further — additional encode passes and uploading are out of scope.
