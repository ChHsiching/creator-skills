# video-download — Reference

Loaded on demand from [SKILL.md](SKILL.md). The main skill file is the pipeline skeleton; this file holds cookie negotiation, raw commands, and gotchas you consult only when something needs explaining or cook isn't available.

## Why cook exists

The download step used to be three steps of hand-assembled yt-dlp commands. Three bugs recurred:

1. **stdout redirect swallowed downloads** — `yt-dlp ... --dump-json > file.json` redirected both the JSON and yt-dlp's progress/trigger output, sometimes resulting in exit 0 with no mp4 written. cook uses `--print-to_file` (yt-dlp's native JSON-to-file option).
2. **Thumbnail misnamed** — yt-dlp's `-o "<name>.raw.%(ext)s"` template leaves the `.raw` infix in the thumbnail name too, producing `<name>.raw.jpg` instead of the documented `<name>.jpg`. The old skill doc claimed `--convert-thumbnails jpg` would fix this; it doesn't (it only changes the extension). cook renames it.
3. **Cookie negotiation hand-driven** — the agent had to detect browsers, try each, manage the Chromium database lock, copy to temp dirs, and never confuse "wrong browser" with "broken cookies". cook drives this internally.

If cook is not installed, the commands below still work — just be aware of the three traps.

## Cookie negotiation — the full table

When a cookieless `-F` hits the YouTube bot wall (error string containing "Sign in to confirm you're not a bot" or "bot"), cook negotiates a `--cookies-from-browser` value internally. The candidates, tried in order:

| Browser | yt-dlp name | Windows profile |
|---|---|---|
| Firefox | `firefox` | `%APPDATA%\Mozilla\Firefox\Profiles` |
| Chrome | `chrome` | `%LOCALAPPDATA%\Google\Chrome\User Data` |
| Edge | `edge` | `%LOCALAPPDATA%\Microsoft\Edge\User Data` |
| Brave | `brave` | `%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data` |
| Doubao (豆包) | `chromium:<profile-path>` | `%LOCALAPPDATA%\Doubao\User Data` |

Firefox/Chrome/Edge/Brave are read directly by brand and are the only four cook auto-tries (it checks each profile dir exists first to skip browsers that aren't installed). Doubao and other Chromium forks need the `chromium:<profile-path>` form because yt-dlp doesn't recognize their brand — **cook does NOT auto-try Doubao**, the form is documented here for manual `--cookies-from-browser` use only.

### The temp-directory workaround (when direct reads all fail)

Two failure modes survive the direct-read pass:
1. A Chromium browser holding an exclusive lock on its Cookies database.
2. A Chromium fork yt-dlp can't read in-place.

cook does NOT implement this workaround — when all four auto-tries fail, cook stops and reports failure. The agent must perform the temp-directory copy manually:

**Ask the user which browser they're logged into the target site with** — don't guess; "wrong browser" and "broken cookies" produce identical failures.

Kill that browser's processes first (closing the window isn't enough — Chromium leaves background processes holding the lock):

```
taskkill /F /IM <browser>.exe
tasklist | findstr /I "<browser>"   # verify nothing remains
```

Then copy both the Cookies database and its encryption key (Chromium encrypts cookie values with a key stored in `Local State`):

```
mkdir -p "<cookies-dir>\Default\Network"
copy "<UserData>\Default\Network\Cookies" "<cookies-dir>\Default\Network\Cookies"
copy "<UserData>\Local State" "<cookies-dir>\Local State"
```

Use a **Windows-native absolute path** for `<cookies-dir>`. Do not use a Git-Bash `/tmp/...` path — yt-dlp's cookie loader rejects it with "could not find chromium cookies database". Then retry with `--cookies-from-browser "chromium:<cookies-dir>"`.

If everything fails: report which browsers were tried, ask the user to log in somewhere and re-run. Stop — more guessing won't help.

## Raw yt-dlp commands cook runs internally

### Probe formats (Step 1 internally)
```
yt-dlp --js-runtimes node --remote-components ejs:github -F "<URL>"
```
`-F` lists formats without downloading. `--js-runtimes node --remote-components ejs:github` solves the n-challenge on sites that use one (YouTube especially); harmless elsewhere. Evaluate: real video/audio formats in the table → cookies not needed; "Sign in to confirm you're not a bot" → cookie negotiation.

### Download (Step 1 internally)
```
yt-dlp --js-runtimes node --remote-components ejs:github \
  [--cookies-from-browser "<source>"] \
  -f "bestvideo+bestaudio" --merge-output-format mp4 \
  --write-thumbnail --convert-thumbnails jpg \
  --print-to-file "%(all)j" "<output-root>/raw/<name>.source.json" \
  -o "<output-root>/raw/<name>.raw.%(ext)s" \
  "<URL>"
```

Flag notes:
- `-f "bestvideo+bestaudio"` picks the highest-resolution video and highest-bitrate audio streams separately; `--merge-output-format mp4` muxes them. Sites that serve video and audio as separate adaptive streams above 720p (YouTube, others) require this to get 1080p+ with sound. Falls back to best muxed format automatically if the site only offers muxed streams.
- For quality cap: replace with `-f "bv*[height<=1080]+ba/b[height<=1080]"` (cook's `--quality 1080` does this).
- `--write-thumbnail --convert-thumbnails jpg` writes the best-scored thumbnail normalized to jpg.
- `--print-to-file` takes **two separate arguments**: a template (`%(all)j` = the full info-dict as JSON) and a target path. This is the **safe** alternative to `--dump-json > file.json` (which can swallow the download via stdout redirect). cook uses the Python API equivalent (`print_to_file` option with a dict `{template: path}`) so the syntax here is the CLI form for manual use.
- `-o "<output-root>/raw/<name>.raw.%(ext)s"` — the literal `.raw` infix is intentional for the video (lands as `<name>.raw.mp4`), but it also affects the thumbnail (lands as `<name>.raw.jpg`). cook renames the thumbnail to `<name>.jpg` after download.

### Verify (Step 1 internally)
```
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "<output-root>/raw/<name>.raw.mp4"
```
The `:nokey=1` suffix makes ffprobe print only the duration value (`4480.034000`), not `duration=4480.034000` — so `float(output)` parses cleanly. `duration > 0` = well-formed, playable mp4.

## Environment details

### yt-dlp binary vs pip package

Two ways yt-dlp can be available:
- **pip package** (`yt-dlp[default]` in requirements.txt): Python module, cook's preferred form.
- **Project-local binary** (`./yt-dlp.exe` on Windows): preferred by the old skill docs because yt-dlp's challenge-solving EJS scripts drift out of date and a project-local binary is a known-fresh copy you control.

The PyInstaller-bundled `.exe` ships the EJS scripts already; no separate install. To get a fresh binary locally:
```
# Windows
curl.exe -L -o yt-dlp.exe https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe
# macOS/Linux
curl -L -o yt-dlp https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp && chmod +x yt-dlp
```
Take the full `yt-dlp.exe`, never `yt-dlp_min.exe` (the min build ships without the EJS scripts).

The `/latest/download/` path always serves the newest release. If a binary is stale (Step 1's `-F` returns only storyboard on a JS-challenge site), re-download over the existing file and retry.

### Node.js

yt-dlp solves the n-challenge in a JavaScript runtime. The default is Deno, which most Windows machines don't have — that's why `--js-runtimes node` is required. `--remote-components ejs:github` tells yt-dlp to fetch the current EJS challenge-solving scripts from GitHub (the bundled ones drift). Check `node --version`; require >= 22.0.0. Required only when the site needs JS challenge solving; harmless otherwise.

### ffmpeg

Required for merging video + audio streams. Run `ffmpeg -version`; if missing, tell the user to install it.

## Gotchas

- **A fresh binary still couldn't solve the challenge.** If `-F` returns only storyboard images on a JS-challenge site even after re-downloading the latest GitHub release and confirming `--js-runtimes node --remote-components ejs:github`, the site has changed its challenge faster than yt-dlp has caught up. Check [yt-dlp issues](https://github.com/yt-dlp/yt-dlp/issues) for current status. Per-site quirks are in yt-dlp's [support list](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

## Degraded completion

The source JSON and the thumbnail are degraded-completion artifacts:
- Some sources have no thumbnail at all.
- A transient `--dump-json` / `--print-to-file` failure shouldn't block the download.

If either is missing, tell the user explicitly:
- **No thumbnail**: they'll need a frame-grab cover later (`ffmpeg -ss <time> -i <mp4> -frames:v 1 cover.jpg`). `video-subtitle` Step 6's `cook cover` handles this.
- **No source JSON**: downstream metadata will have to be re-fetched if needed.

The video itself counts as done as long as `ffprobe duration > 0`.

To preview which thumbnails a source offers before downloading, swap the probe's `-F` for `--list-thumbnails`.
