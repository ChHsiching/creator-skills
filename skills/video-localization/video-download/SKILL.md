---
name: video-download
description: Download a video at the best available quality as a single mp4, from YouTube or any of the thousand-plus sites yt-dlp supports (Bilibili, X (Twitter), Vimeo, etc.). Use when the user wants to download a video, mentions 下载视频 / 生肉下载 / yt-dlp, or gives a URL to fetch.
---

Download a video at the **best available quality** as a single merged mp4, plus its source metadata and cover thumbnail. Uses [yt-dlp](https://github.com/yt-dlp/yt-dlp). This skill handles the defenses you'll hit on the hard ones — YouTube's **n-challenge** (JavaScript signature) and **login wall**, site-specific geo-blocks — by pairing yt-dlp with a Node runtime and, where needed, browser cookies.

Deterministic execution (yt-dlp command assembly, cookie negotiation, thumbnail rename, ffprobe verify) is handled by the [`cook`](https://github.com/ChHsiching/video-cook) CLI. The agent focuses on decisions cook can't make: confirming output paths with the user, deciding when to ask which browser they're logged in with. If cook is not installed, the raw yt-dlp commands still work — see REFERENCE.md.

## What you produce

Three files, all sharing one `<name>` stem, all under `raw/` in a per-video output directory:

1. `<name>.raw.mp4` — best available quality, video + audio merged into one file
2. `<name>.source.json` — the source's full metadata (title, uploader, description, duration, upload date, URL, thumbnail). Captured so downstream work doesn't re-fetch.
3. `<name>.jpg` — the source video's cover thumbnail (best-scored by yt-dlp, normalized to jpg)

## Where the outputs land

```
<output-root>/
└── raw/
    ├── <name>.raw.mp4
    ├── <name>.source.json
    └── <name>.jpg
```

- **`<output-root>`** defaults to `<cwd>/<author>/<video-name>/`. `<author>` from uploader/channel, `<video-name>` from title, both lowercased with separators normalized to `-`. User can override either.
- **`<name>`** defaults to `<video-name>`. User can override.
- **`raw/`** holds the original download.

This layout shares the directory convention with `video-subtitle` — a downstream subtitle skill finds all three files at `<output-root>` + `<name>`.

## The pipeline

### Step 0 — Environment check

```
cook doctor
```

Confirms `yt-dlp`, `node` (>=22, for YouTube n-challenge), and `ffmpeg` are available. If anything is missing, tell the user what to install (cook can't install ffmpeg or node — those need the user).

Note: yt-dlp's challenge-solving EJS scripts drift out of date. cook prefers a project-local `yt-dlp.exe` (or `yt-dlp` on Unix) when one exists — a known-fresh binary you control. If none exists locally and the pip-installed yt-dlp is too stale to solve the current challenge, the user can drop a fresh binary in the project dir. See REFERENCE.md.

Done when `cook doctor` reports `yt_dlp`, `node`, and `ffmpeg` installed.

### Step 1 — Download with cookie negotiation

```
cook download <url> [--author <author>] [--name <name>] [--quality 1080] [--cookies-from-browser <browser>]
```

cook does the whole download in one shot:
- Probes the URL with `-F` (no cookies first)
- If the probe hits the YouTube bot wall (error containing "Sign in to confirm you're not a bot" or "bot"), cook negotiates a cookie source internally: tries each installed browser (firefox → chrome → edge → brave) until one works. If none works, cook stops and asks the user which browser they're logged in with — **don't guess**; trying a browser where they aren't logged in wastes a cycle and the failure looks identical to "cookies broken".
- Downloads video + audio (best quality, or capped with `--quality`), merges to mp4 via ffmpeg
- Writes `<name>.source.json` via `--print-to_file` (the safe way — the old `--dump-json > file.json` stdout redirect silently swallowed downloads)
- Writes the thumbnail and renames it from `<name>.raw.jpg` to `<name>.jpg` (yt-dlp's `-o` template leaves the `.raw` infix in the thumbnail name; cook fixes it)
- Runs `ffprobe` to verify `duration > 0`

cook derives `<author>` and `<name>` from the source metadata (uploader / title). **Confirm these with the user before downloading** — they set the filename stem for every downstream artifact, and cook writes files to that path during download (there is no "rename afterward" path). Pass `--author` and `--name` to override the defaults.

**Quality override:** by default cook takes the best quality the source offers. If the user asked for less ("1080p is fine", "skip 4K"), pass `--quality 1080` (caps height; falls back to the best muxed stream at or under that height). Only cap when the user asks.

Done when `cook download` exits 0 and the JSON output reports `duration > 0`, `thumbnail_renamed: true`, and `source_json_present: true`. If `thumbnail_renamed` is false or `source_json_present` is false, tell the user explicitly — these are degraded-completion artifacts (some sources have no thumbnail; a transient JSON failure shouldn't block the download) but downstream will need to know (frame-grab cover later, metadata re-fetch).

## Handoff

When `cook download` reports done, tell the user the files are ready in `<output-root>/raw/`, sharing the stem `<name>`. If they want subtitles next, point the subtitle skill at `<output-root>` and `<name>` — all three files are findable at that path. Don't run the subtitle skill from inside this one; the user may want to review the raw video first.

## Reference

The following details are consulted on demand — load when the situation calls for it:

- **[REFERENCE.md](REFERENCE.md)** — the full cookie negotiation table (Firefox/Chrome/Edge/Brave/Doubao profile paths), the Chromium-database-lock failure mode and the temp-directory copy workaround, the raw yt-dlp commands cook runs internally (for running without cook), the YouTube n-challenge gotcha, the degraded-completion rules in detail.
