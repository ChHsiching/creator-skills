---
name: novel-copywrite
description: Use when the user wants to turn a scouted novel into a promotion work order — mentions 写文案/推文文案/口播稿/novel-copywrite, hands over a scouted.json from fanqie-scout, or asks "帮我把这本书写成推文". Reads the novel's first chapters from scouted.json, picks the 3 most dramatic chapters, suggests a 4-char alias, and writes two voiceover scripts (a 30-second hook version and a 3-minute full version). Outputs a markdown work order ready for the novel-promo pipeline.
---

# novel-copywrite

**Copywrite** a scouted novel into a promotion work order: read the first chapters, pick the 3 most dramatic, suggest a 4-char alias, write a hook version (30s) and a full version (3min) of voiceover script. Input is a `scouted.json` from fanqie-scout. Output is a markdown work order with the alias + both scripts, ready for novel-promo to turn into video.

The skill copywrites — it does not scout books (fanqie-scout's job), make videos (novel-promo's job), or apply for the alias on 达人中心 (the user does this).

## The contract

```
inputs  : scouted.json (from fanqie-scout) + target book_id
outputs : <out-path>/<book-title>_<date>.md  (the work order)
```

**Done** means the work order markdown exists, contains a 4-char alias, a hook script (120-180 chars), and a full script (800-1200 chars), all matching the original novel's person and tense.

## Step 0 — Resolve inputs

Ask the user (or read from the calling skill):

1. **scouted.json path** — from fanqie-scout. Must contain `books[].chapters[].content`.
2. **target book_id** — which book in the json to copywrite. If only one book, use it. If multiple, ask which (or copywrite all worth_promoting ones).
3. **out_path** — where to write the work order markdown. Default: current directory.

If scouted.json is missing or has no chapters, stop and tell the user to run fanqie-scout first.

**Done when** you can name the scouted.json path, the target book, and the out_path.

## Step 1 — Read the novel and pick 3 chapters

Read the target book's chapters from scouted.json. The book has up to 5 chapters (whatever fanqie-scout fetched).

Pick **the 3 consecutive chapters with the densest dramatic conflict**. Usually this is chapters 1-3 (novel openings front-load hooks), but not always — if chapter 1 is slow worldbuilding and chapters 2-4 have the real conflict, pick 2-4. Consecutive means no gaps (the script reads as one flow).

Judgment criteria for "densest conflict":
- A reversal or twist (character discovers something, status flips)
- Direct confrontation (dialogue clash, physical threat)
- A hook question planted in the reader's mind ("will he survive?" "who is she really?")

Avoid chapters that are pure worldbuilding, travel, or slice-of-life with no tension.

Record the chosen chapter range (e.g. "第1-3章" or "第2-4章") — it goes in the work order.

**Done when** you can name the 3 consecutive chapters chosen and why (one line each, citing the specific conflict in each).

## Step 2 — Determine person and tense

Read the original chapters. Determine:

- **Person**: does the novel use 第一人称 (我) or 第三人称 (他/她)? Most male-audience novels on 番茄 use first person; female-audience varies. The script must match.
- **Tense**: the script always uses **present tense** (我握着, 她说), even if the original uses past tense. Present tense creates urgency for voiceover.

Record the person. The hook and full scripts must use it consistently.

**Done when** you can state the person (第一/第三) and have confirmed the original uses it.

## Step 3 — Suggest the alias

Suggest **two candidate aliases** in different styles, so the user can pick. The hard constraint is passing 番茄's duplicate check — aliases too similar to the book title, character names, or hot titles get rejected with "与热门作品/作者/主演角色名相似度高".

Rules:
- **Exactly 4 characters** each — not 3, not 5. Four is the sweet spot for typing from memory after hearing it once.
- **Common characters only** — no 生僻字. If a candidate would need 玖/柒/栀/玦/玥, rephrase using common characters.
- **Pass the duplicate check** — avoid any 2-char substring that appears in the book title, the main characters' names, or common genre phrases (穿书/重生/反派/系统/豪门 are all high-collision).
- **Provide two styles**:
  - **Style A — 关联型 (related)**: derived from a unique prop, scene, or running gag in the first 3 chapters — NOT from the title or character names. Connects to what the viewer heard in the hook, but via a side door (an object, an action, a phrase) rather than the title's own words.
  - **Style B — 无关型 (unrelated)**: a completely unrelated but memorable + unique 4-char phrase. Functions like a password — its only job is being easy to remember, easy to spell, and unique enough to pass the duplicate check. No connection to the plot needed.

The user picks one and applies for it on 达人中心 themselves.

Example for 《穿书反派，把阴湿女主养成病娇了》:
- Style A: `剪刀不剪了` (from the opening-scene prop — protagonist throws the scissors instead of cutting)
- Style B: `绿茗茶香` (unrelated, but unique + all common chars + easy to type)

**Done when** you have two 4-char candidates, each using common characters, each unlikely to trip the duplicate check (no 2-char substring overlap with the title/character names).

## Step 4 — Write the hook script (30-second version)

Write the **hook script** — 120-180 Chinese characters, designed to be spoken in ~30 seconds. This is the short-form version for platforms that favor quick hooks (抖音/快手 main feed).

**Hook structure** (apply in this order — every hook script follows these 6 beats):

1. **Scene image** (1 sentence) — where is the protagonist, what are they doing? Concrete sensory detail. ("我握着剪刀站在阴暗巷子里")
2. **Counterparty description** (1 sentence) — who's in front of them, what do they look like? Visual, specific. ("面前是个嘴角带淤青、骨瘦嶙峋的少女")
3. **Counterparty's attitude** (1 sentence) — how do they look at the protagonist? Hostile, afraid, contemptuous? ("她看我的眼神像淬了冰的刀子")
4. **Core conflict reveal** (2-3 sentences) — the most dramatic information: what's the stakes, what will happen, what does the protagonist realize? This is the hook's payload. ("我刚穿到这具身体里就反应过来——原主为讨好绿茶女反派要剪她头发，可她是京城第一豪门丢失多年的千金，以后会把原主关地下室折磨三个月再喂鱼")
5. **Protagonist's reversal** (1 sentence) — the protagonist breaks from the expected script, does the unexpected. ("我把剪刀狠狠扔进水槽")
6. **Cliffhanger action + "..."** (1 sentence) — protagonist moves toward the next beat, cut off mid-action. ("然后朝着那少女走过去，想给她递瓶水缓和下关系...")

After the "...", append one line: `（搜索"[alias]"看后续）` — this is the call-to-action that drives viewers to 番茄小说 to search the alias.

**The hook must be self-contained** — a viewer who only watches 30 seconds gets the complete dramatic setup. Don't reference chapters they haven't seen.

**Done when** the hook is 120-180 chars, follows all 6 beats in order, uses the correct person + present tense, ends with "..." + the search call-to-action.

## Step 5 — Write the full script (3-minute version)

Write the **full script** — 800-1200 Chinese characters, ~3 minutes spoken. This is the long-form version for platforms that allow longer narratives (B站/西瓜/抖音长视频).

**Structure**:
- **Paragraph 1 = the hook** (from Step 4, without the "..." ending — instead flow directly into the next paragraph). This front-loads the tension.
- **Subsequent paragraphs** = expand the 3 chosen chapters in order. Each chapter becomes 1-3 paragraphs. Convert the original prose into voiceover style:
  - **Present tense** (even if original is past)
  - **Match original person** (我 or 他/她)
  - **Tighten prose** — cut description that doesn't drive conflict, keep action and dialogue
  - **Colloquialize dialogue** — make spoken lines sound natural when read aloud, not literary
  - **Add protagonist's interior monologue** where the original implies it ("我心里一紧" / "我嗤笑") — voiceover needs a speaking mind, not just events
- **Ending** — end on a suspense beat from chapter 3, not a resolution. The script should leave the viewer wanting chapter 4 (which is on 番茄小说). No "..." cliffhanger here (that's the hook's job); just end on an unresolved tension.

Refer to `references/example-nieqian.md` for a complete example of this structure. It demonstrates: hook-as-first-paragraph, chapter-by-chapter expansion, first-person present-tense, colloquialized dialogue, interior monologue, suspense ending.

**Done when** the full script is 800-1200 chars, starts with the hook, expands all 3 chosen chapters, uses the correct person + present tense throughout, and ends on suspense.

## Step 6 — Write the work order

Assemble the work order markdown. **The section headings are a contract** — novel-promo (the downstream skill) parses `## 钩子版（30秒）` and `## 完整版（3分钟）` to extract the two scripts. Keep the headings exactly as shown:

```markdown
# <book-title> - <YYYY-MM-DD>

**book_id**: <id>
**别名**: <alias-A> / <alias-B>
**素材章节**: <第X-Y章>
**音频估算时长**: 钩子版 ~30秒 / 完整版 ~3分钟

---

## 钩子版（30秒）

<hook script text here, plain text, no markdown formatting>

---

## 完整版（3分钟）

<full script text here, plain text, no markdown formatting>
```

Rules for the script text inside each section:
- **Plain text only** — no `**bold**`, no bullet points, no headings. novel-promo reads everything between the section heading and the next `---` as the script.
- **Each script is one continuous block** — don't insert blank lines or sub-headings within it (narrate-video's sentence splitter handles paragraphing internally).

Write to `<out-path>/<book-title>_<date>.md`. Use the book title from scouted.json; strip characters unsafe for filenames (？/！/ etc.).

**Done when** the markdown file exists at the path, contains both `## 钩子版（30秒）` and `## 完整版（3分钟）` headings, and each section has script text (no placeholders).

## Step 7 — Report

Tell the user:

- The work order path
- The alias suggested (remind: apply for it on 达人中心 before publishing)
- The chapter range chosen + why
- Hook length (chars) + full length (chars)
- Next step: hand this work order to novel-promo to make the video

Nothing further — making the video and publishing belong to sibling skills.
