"""Scout 番茄达人中心: 抓书单/详情/章节正文 via Playwright.

Strategy: launch chrome with the user's real profile (login state reused),
navigate to fanqie pages, intercept XHR responses to grab JSON. The browser
signs its own a_bogus/msToken — we never touch anti-bot signatures.

Usage:
    python scout.py --mode list --top-n 10 --out books.json
    python scout.py --mode single --book-id 7645556324868049945 --chapters 5 --out book.json
"""
import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path


def chrome_user_data_dir():
    """Return chrome's User Data dir on this OS."""
    if sys.platform == "win32":
        return os.path.join(os.environ["LOCALAPPDATA"], "Google", "Chrome", "User Data")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/Google/Chrome")
    return os.path.expanduser("~/.config/google-chrome")


def is_chrome_running():
    """Check whether chrome is currently running (would lock the profile)."""
    import subprocess
    if sys.platform == "win32":
        try:
            out = subprocess.check_output(["tasklist", "/FI", "IMAGENAME eq chrome.exe"],
                                          stderr=subprocess.DEVNULL, text=True)
            return "chrome.exe" in out.lower()
        except Exception:
            return False
    else:
        try:
            out = subprocess.check_output(["pgrep", "-i", "chrome"],
                                          stderr=subprocess.DEVNULL, text=True)
            return bool(out.strip())
        except Exception:
            return False


async def intercept_json(page, url_pattern, key=None):
    """Navigate and wait for an XHR matching url_pattern, return its JSON.
    url_pattern: regex string. If key is given, return data[key], else data."""
    responses = []

    async def on_response(response):
        if re.search(url_pattern, response.url):
            try:
                j = await response.json()
                responses.append(j)
            except Exception:
                pass

    page.on("response", on_response)
    return responses


async def fetch_book_list(context, top_n=10):
    """Fetch the popular_book list. No login required."""
    page = await context.new_page()
    responses = []

    async def on_response(response):
        if "popular_book/list" in response.url:
            try:
                j = await response.json()
                responses.append(j)
            except Exception:
                pass

    page.on("response", on_response)
    await page.goto("https://kol.fanqieopen.com/page/task", wait_until="networkidle", timeout=60000)
    # Give it a moment for the XHR to land
    await page.wait_for_timeout(3000)
    await page.close()

    if not responses:
        return []
    books = responses[0].get("data", {}).get("book_list", []) or []
    return books[:top_n]


async def fetch_book_detail(context, book_id):
    """Fetch single book detail. Login required (cookies from profile)."""
    page = await context.new_page()
    responses = []

    async def on_response(response):
        if "content/book/list/by_conf" in response.url:
            try:
                j = await response.json()
                responses.append(j)
            except Exception:
                pass

    page.on("response", on_response)
    url = f"https://kol.fanqieopen.com/page/content/book-detail?tab_type=2&top_tab_genre=-1&book_id={book_id}&genre=0"
    await page.goto(url, wait_until="networkidle", timeout=60000)
    await page.wait_for_timeout(3000)
    await page.close()
    return responses[0] if responses else None


async def fetch_chapter_list(context, book_id):
    """Fetch the chapter directory for a book. Login required."""
    page = await context.new_page()
    responses = []

    async def on_response(response):
        if "content/chapter/list" in response.url:
            try:
                j = await response.json()
                responses.append(j)
            except Exception:
                pass

    page.on("response", on_response)
    # Just visiting the book-detail page triggers chapter/list XHR
    url = f"https://kol.fanqieopen.com/page/content/book-detail?tab_type=2&top_tab_genre=-1&book_id={book_id}&genre=0"
    await page.goto(url, wait_until="networkidle", timeout=60000)
    await page.wait_for_timeout(3000)
    await page.close()
    if not responses:
        return []
    return responses[0].get("data", {}).get("chapter_list", []) or []


async def fetch_chapter_contents(context, book_id, chapter_items, max_chapters=5):
    """Fetch the content of the first max_chapters chapters by navigating to
    each chapter page and intercepting chapter/detail XHR."""
    page = await context.new_page()
    contents = []

    for i, ch in enumerate(chapter_items[:max_chapters]):
        item_id = ch.get("item_id")
        if not item_id:
            continue
        responses = []

        async def on_response(response, _iid=item_id):
            if "content/chapter/detail" in response.url and _iid in response.url:
                try:
                    j = await response.json()
                    responses.append(j)
                except Exception:
                    pass

        page.on("response", on_response)
        url = (f"https://kol.fanqieopen.com/page/content/book-detail?"
               f"tab_type=2&top_tab_genre=-1&book_id={book_id}&genre=0&item_id={item_id}")
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(2500)
        page.remove_listener("response", on_response)
        if responses:
            data = responses[0].get("data", {})
            contents.append({
                "index": data.get("index", ch.get("index")),
                "title": data.get("chapter_name", ch.get("chapter_name")),
                "content": data.get("content", ""),
            })
        else:
            contents.append({
                "index": ch.get("index"),
                "title": ch.get("chapter_name"),
                "content": "",
            })

    await page.close()
    return contents


def strip_html(s):
    """Strip <p> tags from chapter content, keep paragraph breaks."""
    s = re.sub(r"<p>", "", s)
    s = re.sub(r"</p>", "\n\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    return s.strip()


def slim_book(book):
    """Reduce a popular_book entry to the fields we care about."""
    cats = [c.get("category_name") for c in (book.get("categories") or [])]
    return {
        "book_id": str(book.get("book_id", "")),
        "title": book.get("book_name", ""),
        "author": book.get("author", ""),
        "categories": cats,
        "word_count": book.get("word_num", 0),
        "score": book.get("score", 0),
        "exclusive": bool(book.get("is_exclusive", 0)),
        "completed": book.get("creation_status", 0) == 1,
        "chapter_count": book.get("chapter_num", 0),
        "abstract": book.get("book_abstract", ""),
    }


async def run(args):
    from playwright.async_api import async_playwright

    if is_chrome_running():
        print("FATAL: chrome is running. Close ALL chrome windows first (the profile "
              "is locked while chrome uses it), then re-run.", file=sys.stderr)
        sys.exit(2)

    user_data = chrome_user_data_dir()
    if not os.path.exists(user_data):
        print(f"FATAL: chrome User Data dir not found: {user_data}", file=sys.stderr)
        sys.exit(1)

    async with async_playwright() as p:
        # Launch chrome with the real profile (login state + cookies reused).
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data,
            channel="chrome",
            headless=False,  # needed: a_bogus/js challenge can break in headless
            args=["--disable-blink-features=AutomationControlled"],
        )

        try:
            if args.mode == "list":
                print(f"[1/3] fetching popular_book top {args.top_n}...", flush=True)
                raw_books = await fetch_book_list(context, args.top_n)
                print(f"  got {len(raw_books)} books", flush=True)

                slim_books = [slim_book(b) for b in raw_books]
                print(f"[2/3] fetching chapters for each book...", flush=True)
                for i, sb in enumerate(slim_books):
                    print(f"  [{i+1}/{len(slim_books)}] {sb['title']}", flush=True)
                    chapters = await fetch_chapter_list(context, sb["book_id"])
                    chapter_contents = await fetch_chapter_contents(
                        context, sb["book_id"], chapters, max_chapters=args.chapters)
                    # strip HTML from content
                    for c in chapter_contents:
                        c["content"] = strip_html(c["content"])
                    sb["chapters"] = chapter_contents
                print(f"[3/3] done", flush=True)
                out = {"scouted_at": _today(), "books": slim_books}

            else:  # single
                print(f"[1/2] fetching detail for book_id={args.book_id}...", flush=True)
                detail = await fetch_book_detail(context, args.book_id)
                chapters = await fetch_chapter_list(context, args.book_id)
                chapter_contents = await fetch_chapter_contents(
                    context, args.book_id, chapters, max_chapters=args.chapters)
                for c in chapter_contents:
                    c["content"] = strip_html(c["content"])

                sb = None
                if detail and detail.get("data"):
                    # detail API nests book info differently; fall back to list shape
                    d = detail["data"]
                    sb = {
                        "book_id": str(args.book_id),
                        "title": d.get("book_name", ""),
                        "author": d.get("author", ""),
                        "categories": [c.get("category_name") for c in (d.get("categories") or [])],
                        "word_count": d.get("word_num", 0),
                        "score": d.get("score", 0),
                        "exclusive": bool(d.get("is_exclusive", 0)),
                        "completed": d.get("creation_status", 0) == 1,
                        "chapter_count": d.get("chapter_num", 0),
                        "abstract": d.get("book_abstract", ""),
                    }
                if sb is None:
                    sb = {"book_id": str(args.book_id), "title": "(unknown)"}
                sb["chapters"] = chapter_contents
                print(f"[2/2] done", flush=True)
                out = {"scouted_at": _today(), "books": [sb]}
        finally:
            await context.close()

    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDONE: wrote {args.out}", flush=True)
    print(f"  books: {len(out['books'])}", flush=True)


def _today():
    import datetime
    return datetime.date.today().isoformat()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["list", "single"], default="list")
    p.add_argument("--top-n", type=int, default=10)
    p.add_argument("--book-id", default=None)
    p.add_argument("--chapters", type=int, default=5,
                   help="how many chapters of content to fetch per book (default 5)")
    p.add_argument("--out", default="scouted.json")
    args = p.parse_args()

    if args.mode == "single" and not args.book_id:
        p.error("--mode single requires --book-id")

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
