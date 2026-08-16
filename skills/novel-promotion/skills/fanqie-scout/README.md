# fanqie-scout-skill

A [skill](https://github.com/anthropics/agent-skills) for AI coding agents (Claude Code, Cursor, etc.) that **scouts 番茄达人中心** for novels worth promoting.

Give it a mode (list or single book_id), and it:
1. Launches chrome via Playwright with your real profile (login reused — you must have logged into kol.fanqieopen.com in chrome once)
2. Grabs the popular book list (Top N) or a single book's detail
3. Fetches the chapter directory + first 5 chapters of each book
4. Has the agent judge whether each book is worth promoting
5. Suggests a promotion alias (no obscure characters) for each worth-promoting book

Output is `scouted.json` — structured data ready for downstream skills (novel-promo pipeline).

## What it does

```
mode (list/single) + book_id
   ↓
[Playwright + chrome profile] navigate fanqie pages, intercept XHR JSON
   ↓
scouted.json: book metadata + abstract + first 5 chapters
   ↓
[agent] judges worth_promoting + suggests alias
   ↓
scouted.json (enriched) → ready for novel-promo pipeline
```

## What it does NOT do

- Does **not** write promotion copy (another skill's job)
- Does **not** make videos ([novel-promo](https://github.com/ChHsiching/novel-promo-skill)'s job)
- Does **not** apply for the alias on 达人中心 (legally binding — the user does this themselves)

## Install

```bash
npx skills add ChHsiching/fanqie-scout-skill
```

## Prerequisites

- [Google Chrome](https://www.google.com/chrome/) installed
- Logged into https://kol.fanqieopen.com in chrome at least once (60-day session)
- [Playwright](https://playwright.dev/) Python package + chromium browser (`pip install playwright && playwright install chromium`)
- **Chrome must be fully closed** when running this skill — it holds an exclusive lock on the profile Playwright needs to reuse

## Usage

```
/fanqie-scout list 10         # scout Top 10 popular books
/fanqie-scout single 7645556324868049945   # scout one book by id
```

## Anti-bot handling

番茄达人中心 is a 字节系 SPA with `a_bogus`/`msToken` request signatures. This skill **does not construct signatures** — it lets the real chrome browser sign its own requests (the JS that generates these tokens runs naturally in the page), and intercepts the XHR responses to grab the JSON. Zero anti-bot evasion.

## License

MIT
