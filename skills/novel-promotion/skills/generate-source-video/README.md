# generate-source-video-skill

A [skill](https://github.com/anthropics/agent-skills) for AI coding agents (Claude Code, Cursor, etc.) that **gathers material and stitches a silent source video** for novel-narration promotion.

Give it a duration (seconds) and optional keywords, and it:
1. Searches **Pexels** (stock footage) and **YouTube** (long-form satisfying/landscape videos via yt-dlp) in parallel
2. Caches downloaded clips to the OS-conventional cache dir (reused across runs)
3. Stitches the clips with [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) into a vertical 9:16 silent video of the requested duration

Output is a `video.mp4` (no audio track) ready for the [narrate-video](https://github.com/ChHsiching/narrate-video-skill) skill to add voice and subtitles.

## What it does

```
duration + keywords
   ↓
1. Pexels API search + download (fast, no rate-limit risk)
2. YouTube yt-dlp ytsearch + download (long videos, sliced later)
   - rate-limit safe: 8s sleep, 429/402 stops immediately, no evasion
   - cookies: progressive (cookieless → firefox → chrome → edge)
3. MoneyPrinterTurbo cli.py --video-source local (stitcher only:
   no-voice, no-subtitle, no-bgm)
   ↓
video.mp4 (1080x1920, silent, ≥ duration seconds)
```

## What it does NOT do

- Does **not** narrate or subtitle — that's [narrate-video](https://github.com/ChHsiching/narrate-video-skill)'s job
- Does **not** write the script or publish — those are other skills' jobs
- Does **not** download gross material (修蹄/挤痘) — excluded by design for female-audience videos

This skill is the **source-video stage** in a larger novel-promotion pipeline. A future router will orchestrate: script → narration audio → **generate-source-video** → narrate-video → publish.

## Install

```bash
npx skills add ChHsiching/generate-source-video-skill
```

## Prerequisites

- [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) installed (the stitcher engine)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) on PATH (for YouTube material)
- [Node.js 22+](https://nodejs.org/) (yt-dlp needs it for YouTube's n-challenge)
- A browser installed (Firefox recommended — Chrome has a DPAPI cookie bug on Windows)
- [Pexels API key](https://www.pexels.com/api/) (free) — read from MoneyPrinterTurbo's `config.toml`
- [ffmpeg](https://ffmpeg.org/) on PATH
- [uv](https://docs.astral.sh/uv/) for running MoneyPrinterTurbo

## Usage

```
/generate-source-video <output_path> <duration_seconds> [keywords]
```

Or have a router call it with `(duration, keywords, output_path)`.

## Material types

| Type | Default keywords (English) | Audience |
|---|---|---|
| `satisfying` (default) | soap cutting, power washing, rug cleaning | mainstream novel-promotion |
| `landscape` | aerial nature, underwater ocean, rainy city night | female-audience / broad |
| `mixed` | both pools combined | variety |

Pass keywords like `soap cutting satisfying, rug cleaning ASMR` to override.

## License

MIT
