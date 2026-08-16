---
name: generate-source-video
description: Use when the user wants to generate a silent source video from keywords — mentions 找素材/生成视频/素材视频/generate-source-video, hands over a duration plus keywords, or another skill (a future router) hands off "I have the narration audio duration, now make me a matching silent video."
---

# generate-source-video

**Generate** a silent source video for novel-narration promotion by gathering material from two sources in parallel — Pexels (stock footage) and YouTube (long-form satisfying/landscape videos, fetched via yt-dlp) — then stitching the clips with MoneyPrinterTurbo into a vertical 9:16 video of the requested duration. Input is a duration in seconds plus optional keywords. Output is a single `video.mp4` (no audio track) ready for the narrate-video skill to add voice and subtitles.

The skill gathers material and stitches it — it does not narrate, subtitle, write the script, or publish. Those belong to sibling skills (narrate-video, a future router).

## The contract

```
inputs  : duration (seconds, required) + keywords (optional, default satisfying)
output  : <output_path>/video.mp4  (1080x1920, no audio, ≥ duration seconds)
sources : Pexels API + YouTube (via yt-dlp ytsearch)
engine  : MoneyPrinterTurbo cli.py in --video-source local mode
cache   : OS-conventional cache dir, reused across runs
```

**Done** means `<output_path>/video.mp4` exists, plays, has no audio track, is at least `duration` seconds long, and is 1080x1920.

## Step 0 — Resolve inputs

Ask the user (or read from the calling skill) for:

1. **`duration`** (seconds, required). Add ~3s of tail padding so the last spoken word doesn't cut off abruptly — the caller (router) is responsible for adding the padding before passing the number in, but if the user invokes this skill directly, add it here: `padded_duration = duration + 3`.
2. **`output_path`** (directory, required). The directory the final `video.mp4` lands in. Create it if missing.
3. **`keywords`** (optional). Comma-separated search terms. If absent, default to `satisfying` (satisfying/relaxing material — the mainstream novel-promotion default). The user or router may pass `landscape`, `切皂`, `soap cutting satisfying`, etc.
4. **`material_type`** (optional, auto-detected from keywords). Three flavors:
   - `satisfying` — soap cutting, power washing, rug cleaning (default, mainstream)
   - `landscape` — aerial nature, underwater, city night (female-audience / broad)
   - `mixed` — both pools combined

   If keywords contain `风景/landscape/aerial/underwater/city night` → `landscape`. Otherwise → `satisfying`. The skill's keyword pool only covers gentle material (soap, power washing, rug cleaning, nature); gross material (修蹄/hoof trimming, pimple popping) is simply absent from the pool, so it's never gathered — no need to reject anything.

**Done when** you can name `padded_duration`, `output_path`, the resolved `material_type`, and the keyword list.

## Step 1 — Resolve tooling

Probe, never persist a custom config file into the user's home directory. The skill writes no dotfiles anywhere global.

1. **MoneyPrinterTurbo** — the stitching engine. Check candidates in order, use the first whose `cli.py` exists:
   - `$MPT_DIR` environment variable
   - `<workspace>/MoneyPrinterTurbo` (sibling of the output dir's parent)
   - Common locations: `~/Git/novel-promotion/MoneyPrinterTurbo`, `~/MoneyPrinterTurbo`, `~/Documents/MoneyPrinterTurbo`
   - If none, ask the user once for the path (in-memory only).

2. **yt-dlp** — required only if YouTube material is needed (material_type is `satisfying` or `mixed`). Use a project-local binary if present, else the one on PATH. Verify with `yt-dlp --version`. If missing, install per the video-download skill's pattern (`curl -L -o yt-dlp.exe https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe` on Windows).

3. **Node 22+** — yt-dlp needs it to solve YouTube's n-challenge. Check `node --version`; require >= 22.0.0. If missing, tell the user to install it.

4. **Pexels API key** — required only if Pexels material is needed. Read from MoneyPrinterTurbo's `config.toml` (`pexels_api_keys` field). If absent, tell the user to register at https://www.pexels.com/api/ (free) and add the key to MoneyPrinterTurbo's config.

5. **ffmpeg** — `ffmpeg -version`. If missing, tell the user to install it.

**Done when** MoneyPrinterTurbo's `cli.py` path is known, ffmpeg is on PATH, and (for the active material sources) yt-dlp + Node + Pexels key are all resolved.

## Step 2 — Resolve the global material cache

Material is cached at the OS-conventional cache location, reused across all runs and all projects. Never re-download a video already in the cache.

| OS | Path |
|---|---|
| Windows | `%LOCALAPPDATA%\source-material-cache` (i.e. `C:\Users\<user>\AppData\Local\source-material-cache`) |
| macOS | `~/Library/Caches/source-material-cache` |
| Linux | `${XDG_CACHE_HOME:-~/.cache}/source-material-cache` |

Inside the cache, segregate by source so a Pexels clip and a YouTube clip never collide:

```
<cache>/
├── pexels/        <pexels-photo-id>_<dim>.mp4
├── youtube/       <video-id>.mp4
└── manifest.json  optional: keyword → [cached file ids] for fast re-lookup
```

Deduplicate YouTube downloads by video id (filename). Deduplicate Pexels by photo id. If a search returns a video already in the cache, skip the download.

**Done when** the cache dir exists (create if missing) and you can name its absolute path.

## Step 3 — Gather material (two sources, run in parallel)

The goal is enough footage to fill `padded_duration` seconds at 5-second clip switching (MoneyPrinterTurbo default), i.e. `ceil(padded_duration / 5)` distinct source segments. Aim for 1.5× that many to give the stitcher variety.

### 3a. Pexels (always run, fast, no rate limit risk)

Pexels has satisfying material (soap cutting, power washing, rug cleaning — verified). Use the skill's `scripts/fetch_pexels.py`:

```bash
python <skill>/scripts/fetch_pexels.py \
  --keywords "<comma-separated>" \
  --cache "<cache>/pexels" \
  --count <N>
```

It searches the Pexels video API (with a User-Agent header — the CDN 403s requests without one), downloads portrait-orientation 1080p clips (not UHD — Pexels gates UHD behind 403) to the cache, and prints the list of downloaded file paths. Pexels allows ~200 requests/hour — far above what one video needs.

### 3b. YouTube (run if material_type is satisfying or mixed)

YouTube provides the long-form satisfying material that's even richer than Pexels (1-hour soap-cutting compilations, 10-hour drone landscapes). **Prefer long videos and slice them** — one 30-minute download yields ~360 five-second clips, versus 100+ short downloads for the same variety. This conserves the rate-limit budget (guest: ~300 downloads/hour).

Use the skill's `scripts/fetch_youtube.py`:

```bash
python <skill>/scripts/fetch_youtube.py \
  --keywords "<comma-separated>" \
  --cache "<cache>/youtube" \
  --max-videos 2 \
  --min-duration 300 \
  --max-duration 3600 \
  --browser firefox
```

Key flags:
- `--max-videos 2` — download at most 2 long videos per run (sufficient variety, minimal rate-limit spend)
- `--min-duration 300` — only consider videos ≥ 5 minutes; prefer compilations
- `--max-duration 2400` — **cap at 40 minutes**. Satisfying compilations on YouTube are often 1-11 hour marathons (3-30 GB each). 40 minutes yields ~480 five-second slices while keeping each download under ~1 GB.
- `--browser firefox` — cookies source. **Cookies strategy follows the video-download skill's progressive approach**: try cookieless first; on bot-check failure, detect installed browsers and try each (`firefox` → `chrome` → `edge`); stop at the first that works. Chrome on Windows has a known DPAPI decryption bug — if it fails, skip to the next browser rather than retry.

**Rate-limit safety (mandatory)**:
- `--sleep-seconds 8` adds 8s between downloads (well within YouTube's guest budget)
- On HTTP 429 / 402: **stop immediately**, tell the user "YouTube rate-limited this IP, wait a few hours and retry", do not retry or rotate. The skill never tries to evade a block.
- Never re-download a video id that's already in `<cache>/youtube/`.

### 3c. Combine the pools

Collect all downloaded file paths from both 3a and 3b into one list. If the combined pool is smaller than `ceil(padded_duration / 5)` segments, that's OK — MoneyPrinterTurbo will loop/reuse clips, but warn the user that variety is low.

**Done when** you have a comma-separated list of local material file paths to feed MoneyPrinterTurbo.

## Step 4 — Stitch with MoneyPrinterTurbo

Run MoneyPrinterTurbo's CLI in **local-source mode** to stitch the material into one vertical video of the requested duration. We drive the duration by feeding a silent audio file of `padded_duration` seconds — MoneyPrinterTurbo cuts the stitched video to match the audio length.

**First generate the silent audio** with ffmpeg:

```bash
ffmpeg -y -f lavfi -i "anullsrc=r=22050:cl=mono" -t <padded_duration> -c:a libmp3lame -b:a 128k <tmp>/silent.mp3
```

**Then stitch** (launch detached for long durations — use `scripts/windows-detached.ps1` on Windows, `nohup` on macOS/Linux):

```bash
cd <mpt-dir>
uv run python cli.py \
  --video-subject "source" \
  --video-script "placeholder" \
  --video-source local \
  --video-materials "<comma-separated-material-paths>" \
  --video-aspect "9:16" \
  --custom-audio-file "<tmp>/silent.mp3" \
  --no-subtitle-enabled \
  --bgm-type none \
  --video-clip-duration 5 \
  --n-threads 4
```

Critical flags discovered during testing:
- **`--video-script "placeholder"`** — REQUIRED. Without it, MoneyPrinterTurbo tries to call its LLM (default moonshot) to generate a script, which fails if no LLM key is set. The placeholder skips that stage entirely.
- **`--custom-audio-file`** — feeds the silent audio so MoneyPrinterTurbo knows the target duration and cuts the stitched video to match. Don't use `--voice-name no-voice` — that mode estimates duration from text length, not from your `padded_duration`.
- **`--no-subtitle-enabled --bgm-type none`** — skip subtitle/BGM, those belong to narrate-video.

**Done when** MoneyPrinterTurbo reports success and `storage/tasks/<task-id>/final-1.mp4` exists. (Don't use `--stop-at materials` — that stage only returns the material list, no video file.)

## Step 5 — Copy to the output path and strip the audio stream

MoneyPrinterTurbo's `final-1.mp4` contains a (silent) audio track because we fed it a silent audio file. The narrate-video skill's contract requires **no audio track** — strip it during the copy:

```bash
ffmpeg -y -i <mpt-task-dir>/final-1.mp4 -c:v copy -an <output_path>/video.mp4
```

Verify with ffprobe: only a video stream, ≥ `padded_duration` seconds, 1080x1920.

If the stitched video is shorter than `padded_duration` (rare — happens when material was thin), loop it with ffmpeg's `-stream_loop -1` before stripping audio:

```bash
ffmpeg -y -stream_loop -1 -i <mpt-task-dir>/final-1.mp4 -t <padded_duration> -c:v copy -an <output_path>/video.mp4
```

**Done when** `<output_path>/video.mp4` exists, has only a video stream (no audio), is ≥ `padded_duration` seconds, and is 1080x1920.

## Step 6 — Report

Tell the user:

- The absolute path of `video.mp4`
- Duration, resolution, file size
- Material source breakdown: how many clips from Pexels, how many from YouTube (and how many YouTube minutes downloaded)
- Cache hit rate: how many clips were reused vs freshly downloaded
- The material_type used (satisfying / landscape / mixed)

Nothing further — narration, subtitles, and publishing belong to sibling skills.
