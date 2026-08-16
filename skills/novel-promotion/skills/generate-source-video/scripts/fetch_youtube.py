"""Fetch long-form satisfying/landscape material from YouTube via yt-dlp ytsearch.

Strategy:
- Search YouTube with the given keywords (ytsearchN:).
- Filter results to videos >= --min-duration seconds (prefer compilations).
- Download at most --max-videos of them to <cache>/<video-id>.mp4.
- Skip any video already in the cache (deduplicate by video id).
- Sleep --sleep-seconds between downloads to stay within YouTube's guest
  rate limit (~300 downloads/hour).
- On HTTP 429/402: stop immediately and exit non-zero. Do not retry or evade.

Cookies follow video-download skill's progressive approach:
- Try cookieless first (yt-dlp's --default-search handles search natively).
- On bot-check, detect installed browsers and try --cookies-from-browser
  for each in order: firefox → chrome → edge (chrome has a known DPAPI bug
  on Windows; if it fails, move on).
- Stop at the first browser that works.

Usage:
    python fetch_youtube.py --keywords "soap cutting satisfying,power washing" \
        --cache /path/to/cache/youtube --max-videos 2 --min-duration 300 \
        --browser firefox
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def detect_browsers():
    """Return list of browser names whose profile dirs exist on this machine.
    Ordered firefox → chrome → edge (firefox reads cleanly on Windows;
    chrome has a DPAPI decryption bug but still worth trying)."""
    candidates = []
    home = Path.home()
    if sys.platform == "win32":
        local = home / "AppData" / "Local"
        roaming = home / "AppData" / "Roaming"
        checks = [
            ("firefox", roaming / "Mozilla" / "Firefox" / "Profiles"),
            ("chrome", local / "Google" / "Chrome" / "User Data"),
            ("edge", local / "Microsoft" / "Edge" / "User Data"),
        ]
    elif sys.platform == "darwin":
        checks = [
            ("firefox", home / "Library" / "Application Support" / "Firefox"),
            ("chrome", home / "Library" / "Application Support" / "Google" / "Chrome"),
            ("edge", home / "Library" / "Application Support" / "Microsoft Edge"),
        ]
    else:  # linux
        checks = [
            ("firefox", home / ".mozilla" / "firefox"),
            ("chrome", home / ".config" / "google-chrome"),
            ("edge", home / ".config" / "microsoft-edge"),
        ]
    for name, path in checks:
        if path.exists():
            candidates.append(name)
    return candidates


def run_ytdlp(args, cookies_browser=None):
    """Run yt-dlp with the standard JS-runtime + remote-components flags,
    optionally with --cookies-from-browser. Returns (returncode, stdout, stderr)."""
    cmd = [
        "yt-dlp",
        "--js-runtimes", "node",
        "--remote-components", "ejs:github",
    ]
    if cookies_browser:
        cmd += ["--cookies-from-browser", cookies_browser]
    cmd += args
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def search_and_filter(keywords, max_results_per_kw=5, min_duration=300, max_duration=3600, cookies_browser=None):
    """Search YouTube for each keyword, return list of (id, title, duration_sec)
    for videos in [min_duration, max_duration], deduplicated by id."""
    seen_ids = set()
    results = []
    for kw in keywords:
        search = f"ytsearch{max_results_per_kw}:{kw}"
        # Use -J (dump json) to get metadata without downloading
        rc, out, err = run_ytdlp(
            ["--default-search", "ytsearch", "--skip-download", "--dump-json", search],
            cookies_browser=cookies_browser,
        )
        if rc != 0:
            # If bot-check, the caller will retry with a browser; surface the error
            if "Sign in to confirm" in err or "bot" in err.lower():
                return None, err  # signal: need cookies
            print(f"WARN: search '{kw}' failed: {err[:200]}", file=sys.stderr)
            continue
        # yt-dlp --dump-json emits one JSON object per line
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                meta = json.loads(line)
            except json.JSONDecodeError:
                continue
            vid = meta.get("id", "")
            if not vid or vid in seen_ids:
                continue
            duration = meta.get("duration") or 0
            if duration < min_duration:
                continue
            if duration > max_duration:
                # Skip 10-hour marathons — they'd be multi-GB downloads.
                continue
            seen_ids.add(vid)
            results.append({
                "id": vid,
                "title": meta.get("title", ""),
                "duration": duration,
                "url": meta.get("webpage_url") or f"https://www.youtube.com/watch?v={vid}",
            })
        time.sleep(2)  # be polite between searches
    return results, None


def download_video(url, out_path, cookies_browser=None, sleep_after=8):
    """Download a single video to out_path. Returns True on success."""
    rc, out, err = run_ytdlp(
        ["-f", "mp4/best", "--merge-output-format", "mp4",
         "-o", out_path, url],
        cookies_browser=cookies_browser,
    )
    if rc != 0:
        if "429" in err or "402" in err:
            print(f"FATAL: YouTube rate-limited (429/402). Stop and retry later.", file=sys.stderr)
            sys.exit(2)
        print(f"WARN: download failed for {url}: {err[:200]}", file=sys.stderr)
        return False
    time.sleep(sleep_after)
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--keywords", required=True,
                   help="comma-separated search terms (English recommended for volume)")
    p.add_argument("--cache", required=True,
                   help="cache directory (files saved as <video-id>.mp4)")
    p.add_argument("--max-videos", type=int, default=2,
                   help="max videos to download (default 2)")
    p.add_argument("--min-duration", type=int, default=300,
                   help="only consider videos >= this many seconds (default 300)")
    p.add_argument("--max-duration", type=int, default=2400,
                   help="skip videos longer than this (default 2400s = 40min). "
                        "Satisfying compilations on YouTube are often 1-11 hours and 3-30GB each; "
                        "40min yields ~480 five-second slices while keeping each download under ~1GB.")
    p.add_argument("--browser", default=None,
                   help="cookies browser to use; if omitted, try cookieless then auto-detect")
    p.add_argument("--sleep-seconds", type=int, default=8,
                   help="sleep between downloads (default 8s)")
    args = p.parse_args()

    cache_dir = Path(args.cache)
    cache_dir.mkdir(parents=True, exist_ok=True)
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]

    # Step 1: search cookieless first
    print(f"[search] cookieless for: {keywords}", flush=True)
    results, err = search_and_filter(keywords, min_duration=args.min_duration, max_duration=args.max_duration)
    cookies_browser = None
    if results is None and err:
        # Bot-check: need cookies. Resolve browser.
        if args.browser:
            cookies_browser = args.browser
            print(f"[search] bot-check hit; retrying with --cookies-from-browser {cookies_browser}", flush=True)
        else:
            for b in detect_browsers():
                print(f"[search] bot-check hit; trying cookies from {b}", flush=True)
                results, err = search_and_filter(keywords, min_duration=args.min_duration, max_duration=args.max_duration, cookies_browser=b)
                if results is not None:
                    cookies_browser = b
                    break
            if results is None:
                print(f"FATAL: all cookie sources failed. Last error: {err[:200]}", file=sys.stderr)
                sys.exit(1)

        if results is None:
            # retry once with the chosen browser
            results, err = search_and_filter(keywords, min_duration=args.min_duration, max_duration=args.max_duration, cookies_browser=cookies_browser)
            if results is None:
                print(f"FATAL: search failed even with cookies. Last error: {err[:200]}", file=sys.stderr)
                sys.exit(1)

    if not results:
        print(f"[search] no videos >= {args.min_duration}s found for {keywords}", flush=True)
        sys.exit(0)

    # Sort by duration desc — prefer the longest compilations
    results.sort(key=lambda r: r["duration"], reverse=True)
    print(f"[search] {len(results)} candidate videos (sorted by duration desc):", flush=True)
    for r in results[:args.max_videos + 2]:
        print(f"  {r['duration']:>6}s  {r['id']}  {r['title'][:60]}", flush=True)

    # Step 2: download up to max-videos, skipping cached
    downloaded = []
    for r in results:
        if len(downloaded) >= args.max_videos:
            break
        out_path = str(cache_dir / f"{r['id']}.mp4")
        if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
            print(f"[cache] hit {r['id']} (already downloaded)", flush=True)
            downloaded.append(out_path)
            continue
        print(f"[download] {r['id']} ({r['duration']}s) -> {out_path}", flush=True)
        ok = download_video(r["url"], out_path,
                            cookies_browser=cookies_browser,
                            sleep_after=args.sleep_seconds)
        if ok:
            downloaded.append(out_path)

    # Step 3: print the list of available files (cached + freshly downloaded)
    print(f"\nDONE", flush=True)
    print(f"downloaded {len(downloaded)} videos:", flush=True)
    for f in downloaded:
        print(f"  {f}", flush=True)


if __name__ == "__main__":
    main()
