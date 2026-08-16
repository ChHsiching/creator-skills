---
name: fanqie-scout
description: Use when the user wants to scout 番茄达人中心 for novels worth promoting — mentions 选书/找书/番茄/scout/达人中心, gives a 番茄 book_id or URL, or asks "哪些书值得推". Launches chrome via Playwright (reusing the user's login), grabs the popular book list + per-book detail + first 5 chapters, and writes a JSON file for downstream skills (novel-promo, a future copywriting skill).
---

# fanqie-scout

**Scout** the 番茄达人中心 for novels worth promoting. Launch chrome with the user's real profile (login state reused), navigate to fanqie pages, intercept the JSON the SPA's own XHR returns, and write a structured `scouted.json` — book metadata, abstracts, and the first 5 chapters of each book. Then the agent reads that JSON and judges whether each book is worth promoting, plus suggests a promotion alias (no obscure characters).

The skill scouts — it does not write promotion copy, make videos, or apply for the alias on 达人中心. Those belong to sibling skills.

## The contract

```
inputs  : mode (list or single) + book_id (single mode) + chapters (default 5)
outputs : <out-path>/scouted.json  (book metadata + abstract + first N chapters)
engine  : Playwright driving chrome with the user's real profile (login reused)
auth    : user must have logged into kol.fanqieopen.com in chrome once (60-day session)
```

**Done** means `scouted.json` exists, parses as JSON, has a `books` array, and each book has at minimum `book_id`, `title`, `abstract`, `chapters` (with `content` for the first N). Plus the agent has filled `worth_promoting`, `worth_reason`, and `suggested_alias` for each book.

## Step 0 — Resolve inputs and check chrome

Ask the user (or read from the calling skill):

1. **Mode** — `list` (scout the Top N popular books, default N=10) or `single` (scout one book by id).
2. **book_id** — required for single mode. Accept either a raw id or a `kol.fanqieopen.com/...book_id=X...` URL; extract the id.
3. **chapters** — how many chapters of content to fetch per book. Default 5.
4. **out_path** — where to write `scouted.json`. Default: current directory.

Then check chrome state with the script's built-in guard:

```bash
python <skill>/scripts/scout.py --help  # any invocation runs the chrome-running check
```

The script aborts with exit code 2 and a clear message if chrome is running. **Tell the user** to close ALL chrome windows (profile lock — chrome holds an exclusive lock on its User Data dir that blocks Playwright from reusing the login), then re-run. The user said they don't use chrome daily, so this is near-zero cost.

**Done when** you can name `mode`, `book_id` (single) or `top_n` (list), `chapters`, and `out_path`, and the chrome-running check passes.

## Step 1 — Run the scout script

```bash
# list mode
python <skill>/scripts/scout.py --mode list --top-n 10 --chapters 5 --out <out-path>/scouted.json

# single mode
python <skill>/scripts/scout.py --mode single --book-id 7645556324868049945 --chapters 5 --out <out-path>/scouted.json
```

The script:
- Launches chrome via Playwright with `--user-data-dir` pointing at the real profile (login + cookies reused, 60-day session).
- Navigates to the popular list page (`/page/task`) and intercepts the `popular_book/list/v1` XHR for the book list (no login needed for this one).
- For each book, navigates to its detail page and intercepts `content/book/list/by_conf/v1` (detail), `content/chapter/list/v:version` (chapter directory), and `content/chapter/detail/v:version` (per-chapter content) XHRs (login required — satisfied by the profile).
- Lets chrome sign its own `a_bogus`/`msToken` (字节系 anti-bot) — the skill never constructs these.
- Strips `<p>` HTML from chapter content, writes `scouted.json`.

This is slow — ~10s per book (page navigation + XHR wait). Top 10 = ~2 minutes. Tell the user to expect the wait.

**Done when** the script prints `DONE: wrote <out-path>/scouted.json` and exits 0. Read the file; if `books` is empty or any book lacks `chapters`, surface the failure and re-run.

## Step 2 — Judge each book (worth promoting)

Read `scouted.json`. For each book, the agent applies judgment — not a rigid score cutoff. Consider:

- **Score** — 8.0+ is a good sign, but a 7.5 in a hot category can still outperform an 8.5 in a niche one.
- **Category fit** — does the category match a current 番茄 trending track (都市日常/玄幻脑洞/青春甜宠/现言脑洞 are mainstream)? Niche categories convert worse.
- **Word count + completion** — completed books ≥ 20万字 convert better (reader finishes the sample, wants more). Unfinished < 10万字 is risky (reader hits the paywall, no backlog).
- **Exclusive** — `is_exclusive` books get higher CPA on 番茄.
- **Abstract hook** — does the abstract have a clear hook (穿书/重生/反派/系统)? Hooks convert.
- **Chapter 1 opening** — does the first chapter open with conflict (the agent reads it)? Slow openings lose viewers in the first 3 seconds.

For each book write:
- `worth_promoting`: bool
- `worth_reason`: one sentence citing the deciding factor (e.g. "评分8.2 + 都市日常热门赛道 + 完结23万字 + 独家")

For books marked `worth_promoting: true`, the reason must cite at least two concrete data points from the metadata (score, word_count, category, completion status). For books marked `false`, the reason must name the specific weakness (not a generic "low score" — say "评分7.5且分类冷门+未完结仅3万字，前章铺垫冗长").

**Done when** every book in `scouted.json` has `worth_promoting` and a specific `worth_reason` (true books cite 2+ data points, false books name the weakness), and you've rewritten the file.

## Step 3 — Suggest a promotion alias

For each book marked `worth_promoting: true`, suggest a promotion alias (别名). The alias is what readers type into 番茄小说 app to find the book via this promoter — it has to be **easy to spell from hearing** (viewers hear it in the video, then type it).

Rules:
- **4-8 characters** — short enough to remember from a 30-second video.
- **Common characters only** — no 生僻字. If the book title has 玖/柒/栀/玦/玥, find an alternate phrasing. The viewer must be able to type the alias without looking up how to write a character.
- **Keep the alias spoiler-free** — pull from the book's hook (title, protagonist, setup conflict), never from a mid-book twist or reveal.

Examples:
- 《穿书反派，把阴湿女主养成病娇了》 → `反派养女主` ✓ (common chars, from hook); `阴湿病娇` ✗ (阴湿/病娇 are niche terms)
- 《分手后，被一群精神小妹收留了》 → `精神小妹收留` ✓
- 《天眼风水师》 → `天眼风水师` ✓ (already short and common)

Write `suggested_alias` for each worth-promoting book. The skill only **suggests** — the user applies for the alias themselves on 达人中心 (it's a legally binding action with promotion responsibility).

**Done when** every `worth_promoting: true` book has a `suggested_alias` and you've rewritten the file.

## Step 4 — Report

Tell the user:

- How many books scouted, how many worth promoting
- For each worth-promoting book: title, score, category, **suggested alias**, one-line reason
- The absolute path of `scouted.json` (for the downstream copywriting/video skills to consume)
- Reminder: the user must apply for each suggested alias on 达人中心 themselves before publishing videos

Nothing further — writing promotion copy and making videos belong to sibling skills.
