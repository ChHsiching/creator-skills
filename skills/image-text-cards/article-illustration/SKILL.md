---
name: article-illustration
description: Turn a post, article, or video transcript into a set of vertical (3:4) illustrated book-page cards for posting to Xiaohongshu and similar platforms. Each card pairs a 16:9 hand-drawn "小黑" (xiaohei) illustration with handwritten-font text that explains the content faithfully — no AI tone, no editorializing — so a reader can understand it without the source. Use when the user wants to make 图文/教程图文/小红书图文 from a link or content, mentions 小黑插图/手写体卡片/书页排版, or asks to illustrate an article/post/video into shareable image cards.
---

Turn a **source** (a post, article, video transcript, or skill/repo link) into a set of **3:4 vertical illustrated book-page cards**, each pairing a hand-drawn **小黑 (xiaohei)** illustration (16:9) with **handwritten-font text** that explains the content. The agent does the writing and the assembly. Output is ready to post: all image cards + multiple title/body/hashtag options.

This is **faithful illustration, not re-creation**. The pictures and text together let a reader understand the content without re-reading the source. What "faithful" means in practice — every word you write, every example you construct — is in [`WRITING.md`](WRITING.md). Read it before Step 4 on your first run; consult it whenever a sentence feels off.

The skill ships its own `scripts/`, `templates/`, and `assets/fonts/`. They live **inside this skill folder**. Resolve their absolute path before invoking — the user's content may be anywhere.

## What you produce

Every run produces all of these by default (only skip if the user explicitly says so):

1. `NN-*.png` — the cards: **cover + content pages + ending**, in order, each 1080×1440 (3:4)
2. `caption.md` — **multiple** title options (≤20 chars each), multiple body options, a hashtag set, and a sources block (for a pinned comment)
3. `source.md` — the fetched/normalized source content (provenance)
4. `shot-list.md` — the page-by-page plan
5. `README.md` — the index for this run's directory

## Visual identity (fixed unless the user overrides)

- **HTML cards are 3:4 vertical** (1080×1440).
- **小黑 illustrations are 16:9**, embedded in the upper area of each content card. The cover and ending cards are pure HTML + SVG 小黑 blobs — generated cover scenes drift empty and get text painted on the character, so keep them illustration-free.
- **小黑 is a small solid-black blob** (white dot eyes, thin limbs, deadpan), not a big humanoid.
- **Default theme color** `#FBF7EE` (light warm neutral), shared by the HTML CSS and the illustration prompt. The user can name a different color, font, or illustration style; honor it.
- **Fonts stay within the project's two faces** — `FONT_CN` (handwriting body) and `FONT_MONO` (monospace code). Every piece of text, inline styles included, uses one of these two `font-family` values. Distinguish hierarchy by size, color, weight, or a tinted block (the codeblock's warm-neutral pill) — not by introducing a third font.
- **Page numbering defaults to cover = 01.** Cover counts as the first page, ending counts as the last, `TOTAL` equals the card count. A 9-card set runs `01/09 … 09/09`. Alternative — cover = 00, ending = N-1, `TOTAL` = N — is allowed only if the user asks for it. Write the chosen rule at the top of `shot-list.md` and verify every page's `NUM`/`TOTAL` matches before rendering; mixed rules (`00/09` cover with `08/09` last page) read as broken.

## Where the outputs land — one folder per source

Ask where before Step 1 — default is `<cwd>/<source-slug>/`. Inside, split by purpose:

```
<source-slug>/
├── README.md           ← index for this run
├── source.md           ← fetched/normalized source content
├── shot-list.md        ← page-by-page plan
├── caption.md          ← title/body/hashtag options
├── prompts/            ← image prompt file per content page (NN-*.md)
├── illustrations/      ← generated 16:9 小黑 illustrations (NN-*.png)
├── pages/              ← page data JSON (NN-*.json)
└── *.png               ← final 3:4 cards, in order: 01-cover, 02.., NN-ending (cover = 01 by default)
```

## Environment check — resolve before generating

Before Step 1, confirm four things. If any fails, the run breaks downstream.

1. **playwright** resolves from the run directory: `cd <run-dir> && npm i playwright` (the scripts use `createRequire` to resolve it from cwd). Verify with `node -e "require('playwright')"` from the run dir.
2. **Image backend**: detect by env keys — `ZAI_API_KEY`/`BIGMODEL_API_KEY` → zai (GLM-Image); `OPENAI_API_KEY` → openai. If multiple or none, **ask the user** which provider and have them set the key.
3. **Bundled fonts** are in `assets/fonts/`. If the user supplies their own `.ttf`, copy it into the run folder and reference it.
4. **Templates** present: `ls <skill>/templates/` should show `cover.html`, `page.html`, `page-text.html`, `ending.html`, `image-prompt.md`. If any are missing, copy from the source repo.

**Done when** you can name the image provider, confirm playwright resolves, confirm templates exist, and confirm the `--size` flag matches the backend (GLM-Image needs multiples of 32 → `1280x736`; GPT-image has no constraint).

Other environment traps (API keys in .env not exported, codeblock sizing, page-number drift) are catalogued in [`PITFALLS.md`](PITFALLS.md) — consult it when a step misbehaves.

## The pipeline

### Step 1 — Acquire the source content

The user gives a **link** or a **local file**. Acquire by descending fallback:

1. Built-in web fetch / web read tools (fastest). Try this first.
2. **mcp-chrome** for login-walled or bot-checked pages (the user's daily Chrome, login state intact). Detection + install in [`MCP-CHROME.md`](MCP-CHROME.md). Use it if installed. It's recommended for login-walled sources but never a hard dependency.
3. Headless playwright. If the page needs login, **ask the user**; if they decline, fall through.
4. Ask the user to paste the content or point to a local file.

Save normalized content to `source.md`. For skill/repo links, capture the README/content, not just metadata.

**Done when** `source.md` exists and faithfully captures the source (no fabrication). If you're unsure whether a fetch is complete (page may have JS-rendered or collapsed content the fetcher missed), cross-check with a second method or ask the user to confirm — truncated sources produce truncated cards.

### Step 2 — Read deeply, choose cognitive anchors → shot list

Read `source.md`. Extract the **cognitive anchors** — the core judgments, steps, structures, states, or turning points that carry the meaning. Keep them distinct (each anchor earns its own card); weight them as the source does (a one-line mention in the source stays a one-line mention on the card, not a full page).

**Page count follows content, not a fixed number.** As many pages as there are anchors worth their own card. Prefer an extra page that makes a point land over hitting a number.

**Coverage test for how-to / instructional sources.** If the source teaches a method the reader is meant to apply, the plan must include an operable page: one that shows the reader what to actually do, concretely enough to copy. "What it is" and "why it matters" are not enough — a reader who finishes the cards nodding but unable to act has been failed. If the source itself has a worked example, prompt, or step list, that becomes the operable page (rendered verbatim, per Writing rule 2). If it doesn't, flag the gap to the user before generating.

**Templates vs add-pages.** Most content pages are illustrated (use `templates/page.html`, with a 小黑 illustration). But some pages are information-dense and don't need an illustration — official-template breakdowns, Chinese translations of English originals, filled-in example prompts. Those use `templates/page-text.html` (no illustration, full-page text). Decide per page when planning; note which template each page uses in `shot-list.md`.

Write `shot-list.md`, one entry per card:
- page number, position (cover/content/ending), chapter name, **template** (page.html or page-text.html)
- **core meaning** (one sentence)
- **structure type** (Workflow / 系统局部 / 前后对比 / 角色状态 / 概念隐喻 / 方法分层 / 地图路线 / 过程演示)
- **what 小黑 does** (the core action — if removing 小黑 leaves the metaphor intact, it's decoration = fail)
- **a freshly invented low-tech metaphor** (never reuse another page's metaphor, never copy example compositions)
- suggested Chinese labels (short)

Then **STOP and get the user to confirm the shot list.** This gate is mandatory — the shot list is the skeleton; a wrong skeleton wastes image API money on every page.

**Done when** `shot-list.md` exists, every page declares its template, and the user has confirmed (or adjusted it and you've updated the file).

### Step 3 — Confirm style, preview the cover

Ask the user for style preferences (AskUserQuestion or equivalent; fall back to plain numbered options if the question tool fails validation): theme color (default `#FBF7EE`), font (default 霞鹜文楷), image provider if not auto-detected, any reference image/link override.

**Generate the cover first, alone, as a preview.** The cover is pure HTML (`templates/cover.html`) — no generated illustration. Fill its placeholders, render with `scripts/render_page.mjs`, show the user. The cover is the easiest place to drift; confirm direction before batching.

**Title line-break pitfall**: when the cover TITLE wraps an accent word in `<span class="accent">`, the browser may break the line at the span boundary and split a word across two lines. If the rendered title breaks a word, insert an explicit `<br>` where you want the break. Check the rendered PNG, not just the HTML.

**Done when** the user confirms the cover.

### Step 4 — Batch-generate content pages, then the ending

The shot-list gate and cover preview authorized the batch. Generate it, verify each page, then enter the adjust loop. The full rules for writing image prompts, handling failures, and verifying illustrations are in [`IMAGE-PROMPTS.md`](IMAGE-PROMPTS.md) — read it before this step.

For each content page, in order:

1. **Write the image prompt** (for illustrated pages only — text-add pages skip to step 3). Fill `templates/image-prompt.md` for that page's anchor → save to `prompts/NN-*.md`. Follow the rules in IMAGE-PROMPTS.md (exact-hex background, 小黑 = blob, one structure per image, fresh metaphor, element list ≤ 5).
2. **Generate the 16:9 illustration**:
   ```bash
   node <skill>/scripts/gen_image.mjs prompts/NN-*.md illustrations/NN-*.png --size 1280x736
   ```
   For batches, add `--delay 25000` (serial spacing avoids rate limits — see IMAGE-PROMPTS.md).
3. **Verify the illustration** with an image-analysis tool (agent can't see the PNG directly). Confirm: 小黑 is a blob, 小黑 does the core action, no text on 小黑, background color is right, the metaphor holds, no rendering garble. Any failure → fix per IMAGE-PROMPTS.md "content failure" and regenerate.
4. **Fill the page data** → save to `pages/NN-*.json`. Set `ILLO_H` per page (default 600; shrink to 340-520 when the body is long or has codeblocks — the lint step below will tell you).
5. **Render the card**:
   ```bash
   node <skill>/scripts/render_page.mjs <template.html> pages/NN-*.json NN-*.png
   ```
   Run from the run directory (the script writes temp HTML to cwd and resolves font/illustration paths from cwd).
6. **Lint every rendered card**:
   ```bash
   node <skill>/scripts/lint_page.mjs <template.html> pages/NN-*.json
   ```
   If lint reports overflow (`BODY 溢出底部`, `.text 与 .footer 重叠`), shrink `ILLO_H` or trim the body, re-render, re-lint. Repeat until clean.

**Verbatim blocks go in `<div class="codeblock">`.** When a page quotes the source's prompt, code, or command, paste the original text into a `codeblock` div inside the `BODY` field — original language, not translated, not paraphrased. To explain, add a paragraph below the block. See Writing rule 2.

The ending page uses `templates/ending.html` (pure layout + SVG 小黑, no generated illustration).

**Done when** every content card + ending card exists as a PNG **and** every one passes lint (no overflow, no overlap, illustration loaded, fonts loaded). "Files exist" is not enough — a card that exists but overflows the canvas is not done.

### Step 5 — Adjust loop (the task does not end at "generated")

Show the user the full set. **Ask what to adjust.** Adjustments fall into two kinds:
- **Text/layout** (HTML) — free, instant, repeatable. Prefer this when the fix is about wording, a missing point, emphasis, or composition of the text block.
- **Illustration** (regenerate) — costs money. Only when the illustration itself is wrong (composition, 小黑's action, the metaphor doesn't hold).

**Scope discipline.** Every change stays inside the user's ask. A format report means fix the format, full stop — no rewriting the sentence, no "improving" the content alongside, no swapping the metaphor, no adjusting unrelated pages. Scope creep erodes trust faster than the original flaw did. Edit in the smallest unit that resolves the feedback.

**When a change forces a trade-off, surface it; don't route around it in silence.** Making one fix may require giving something up (a bigger font pushes the footer off-canvas; restoring an earlier wording undoes another edit). Pick the option that requires the fewest side-effects, say what you picked and what it cost, and let the user override. Routing around the trade-off by quietly changing five other things is how scope discipline dies.

**CJK ↔ Latin spacing**: every Latin token (English words, numbers, code, model names like `Chat`/`Work`/`Codex`/`GPT-5.6`) gets a space on both sides when adjacent to Chinese. `Chat回答问题` → `Chat 回答问题`. This is a format fix — apply by adding the space, not rewording.

**After each adjust, report state before asking for more.** One or two lines: what changed, what you deliberately left alone, anything you want the user to confirm. Then ask. The user can't tell done from in-progress, and the next round of feedback may be based on a stale mental model.

**Every round of text edits re-runs the wording check.** Before reporting "adjusted", read every changed page's body back to yourself and apply the WRITING.md self-checks (平实陈述 / 正文不比喻 / 重复正文的补充段). The lint script catches overflow; this check catches wording regressions lint can't — coined jargon, overcompressed abbreviations, unexplained terms, invented figures of speech, restated "注：" paragraphs.

**Done when** the user says the set is good (or makes no more changes), **every adjusted page passes lint again**, and **every adjusted page's wording passes the self-check above**.

### Step 6 — Write the posting copy

Write `caption.md`:

- **Multiple title options** (≤20 chars each for Xiaohongshu), **different styles** (e.g. 平实点题型 / 数字钩子型 / 痛点共鸣型). None may overlap with the cover's text. **Count the characters with `scripts/count_title.mjs`** — agent eyeballing is unreliable, especially with English tokens (`GPT-5.6` is 7 chars). Latin letters, digits, spaces, and punctuation each count as one; English-heavy titles blow past 20 fast.
- **Multiple body options**, each faithfully summarizing the content. Plain text, no markdown (Xiaohongshu renders `**` and backticks literally).
- **A hashtag set.**
- **A sources block** listing every link the original source cited (official docs, third-party blogs). The user pastes these into a pinned comment.

**Ending card is reader-facing, not a sources page.** Its NOTE block is a hook — an independent, non-fawning question or observation drawn from the content. Link lists, "来源：...", "见 README" go in the pinned comment, not on the card. The footer already credits the source; repeating it on the NOTE reads as developer thinking.

**Done when** `caption.md` exists with multiple verified titles (≤20 chars each via count_title.mjs), multiple body options, hashtags, and a sources block — **and** each body option passes the WRITING.md wording self-checks.

### Step 7 — README

Write the run's `README.md`: index table (what each file/folder holds), style choices used (theme color, fonts, image backend), and a processing log. A reader who never saw this run should, in 30 seconds, point to the file they need.

**Done when** `README.md` exists with the index, style choices, and log.

## Writing rules — what every word must satisfy

These apply to every word you write (card text, caption, README). The short version is here; the expanded rules with examples live in [`WRITING.md`](WRITING.md).

1. **Faithful to the source.** Only express what the source says. Weight follows the source — one line in the source becoming a full page is editorializing even if every word is technically faithful.
2. **Verbatim where it matters.** The source's prompts, code, commands, and API names are quoted as-is, in their original language. To explain in Chinese, write a paragraph below the verbatim block; don't translate inside it.
3. **No AI tone.** Write like a person. The AI-tone inventory is in WRITING.md — read your draft back against it.
4. **Metaphors explain themselves.** Every metaphor word unpacks its own meaning on first use.
5. **Verify claims the source makes about the world.** Numbers, model names, "the industry calls this X" — these go stale. Carry the source's hedges onto the card.
6. **Plain wording.** Use words the reader already knows. Keep necessary technical terms (they're part of the topic) but gloss them on first use (`DWM（桌面窗口管理器）`). Don't coin Chinese for English jargon, and don't compress a whole sentence into a few characters. Expanded in WRITING.md "用词：平实陈述".
7. **Literal body text.** Metaphor is for the illustration; body text says what it means. Don't reach for colorful figures of speech ("一个爹", "祭天") where plain words are clearer. Expanded in WRITING.md "用词：正文不比喻".

## Platform notes

- Images are always 3:4 vertical (designed for Xiaohongshu; works elsewhere too). Offer other ratios only if the user asks.
- For Xiaohongshu: titles ≤20 chars. The cover card and the posted title use **different** wording.
