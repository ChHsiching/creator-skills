"""Fetch stock footage from Pexels for novel-narration source videos.

Searches the Pexels video API for each keyword, downloads portrait (or square)
clips to <cache>/<photo-id>_<dim>.mp4. Skips any clip already in the cache
(deduplicate by photo id). Pexels allows ~200 requests/hour — far above what
one video needs, so no rate-limit handling is required.

The Pexels API key is read from MoneyPrinterTurbo's config.toml (pexels_api_keys)
by default, or supplied via --api-key.

Usage:
    python fetch_pexels.py --keywords "forest night,temple,moon" \
        --cache /path/to/cache/pexels --api-key <key> --count 6
"""
import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path


def read_pexels_key_from_mpt_config():
    """Try to read pexels_api_keys from MoneyPrinterTurbo's config.toml.
    Returns the first key, or None."""
    # Common locations
    candidates = [
        os.environ.get("MPT_DIR"),
        str(Path.home() / "Git" / "novel-promotion" / "MoneyPrinterTurbo"),
        str(Path.home() / "MoneyPrinterTurbo"),
    ]
    for cdir in candidates:
        if not cdir:
            continue
        cfg = Path(cdir) / "config.toml"
        if not cfg.exists():
            continue
        try:
            text = cfg.read_text(encoding="utf-8")
        except Exception:
            continue
        # simple parse: find pexels_api_keys = ["..."]
        import re
        m = re.search(r'pexels_api_keys\s*=\s*\[\s*"([^"]+)"', text)
        if m:
            return m.group(1)
    return None


def search_pexels(keyword, api_key, per_page=10, orientation="portrait"):
    """Search Pexels videos. Returns list of dicts with id, width, height, duration, file_url."""
    url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(keyword)}&per_page={per_page}&orientation={orientation}"
    req = urllib.request.Request(url, headers={
        "Authorization": api_key,
        "User-Agent": "Mozilla/5.0 generate-source-video/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"WARN: search '{keyword}' failed: {e}", file=sys.stderr)
        return []
    results = []
    for v in data.get("videos", []):
        # Pick the best mp4 file for stitching. Prefer 1080-wide (portrait
        # 1080x1920 matches the target); avoid UHD (2160) which Pexels often
        # gates behind 403. Fall back to 720 if 1080 absent, then anything.
        files = [f for f in v.get("video_files", [])
                 if f.get("file_type") == "video/mp4"]
        if not files:
            continue
        # prefer width near 1080, then 720, then whatever's smallest above 480
        def width_rank(f):
            w = f.get("width", 0)
            if w == 1080: return 0
            if w == 720: return 1
            if w >= 480: return 2
            return 3
        best = min(files, key=width_rank)
        results.append({
            "id": v["id"],
            "width": best.get("width"),
            "height": best.get("height"),
            "duration": v.get("duration", 0),
            "file_url": best["link"],
        })
    return results


def download_clip(url, out_path):
    """Download a clip to out_path with a User-Agent header (Pexels CDN 403s
    requests without one). Returns True on success."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 generate-source-video/1.0",
        })
        with urllib.request.urlopen(req, timeout=60) as resp:
            with open(out_path, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
        return True
    except Exception as e:
        print(f"WARN: download failed {url}: {e}", file=sys.stderr)
        # clean up partial file
        if os.path.exists(out_path):
            try:
                os.remove(out_path)
            except OSError:
                pass
        return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--keywords", required=True,
                   help="comma-separated search terms")
    p.add_argument("--cache", required=True,
                   help="cache directory")
    p.add_argument("--count", type=int, default=6,
                   help="target number of clips to download (default 6)")
    p.add_argument("--api-key", default=None,
                   help="Pexels API key; if omitted, read from MoneyPrinterTurbo config.toml")
    p.add_argument("--orientation", default="portrait",
                   choices=["portrait", "square", "landscape"],
                   help="preferred orientation (default portrait)")
    args = p.parse_args()

    api_key = args.api_key or read_pexels_key_from_mpt_config()
    if not api_key:
        print("FATAL: no Pexels API key. Pass --api-key or add pexels_api_keys to MoneyPrinterTurbo's config.toml", file=sys.stderr)
        sys.exit(1)

    cache_dir = Path(args.cache)
    cache_dir.mkdir(parents=True, exist_ok=True)
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]

    downloaded = []
    seen_ids = set()
    for kw in keywords:
        if len(downloaded) >= args.count:
            break
        print(f"[search] {kw}", flush=True)
        results = search_pexels(kw, api_key, orientation=args.orientation)
        for r in results:
            if len(downloaded) >= args.count:
                break
            if r["id"] in seen_ids:
                continue
            seen_ids.add(r["id"])
            dim = f"{r['width']}x{r['height']}"
            out_path = str(cache_dir / f"{r['id']}_{dim}.mp4")
            if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
                print(f"[cache] hit {r['id']}", flush=True)
                downloaded.append(out_path)
                continue
            print(f"[download] {r['id']} ({dim}, {r['duration']}s)", flush=True)
            if download_clip(r["file_url"], out_path):
                downloaded.append(out_path)
        time.sleep(1)  # be polite

    print(f"\nDONE", flush=True)
    print(f"downloaded {len(downloaded)} clips:", flush=True)
    for f in downloaded:
        print(f"  {f}", flush=True)


if __name__ == "__main__":
    main()
