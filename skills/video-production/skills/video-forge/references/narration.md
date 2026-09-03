# Narration craft

For videos that narrate original content (news briefings, explainers, voiced tool walkthroughs), the narration script IS the material: it is authored here, gated like any transcript, and frozen before synthesis. Series-locked choices (voice, register overrides) come from the user's own series notes where they keep them; this file carries the craft.

## Two tracks, written together

tts-forge defines the split; this file owns the transcription rules (subtitle tracks strip sentence-final punctuation — a video-side rule).

- **Display track** (subtitles, on-screen cards) is the written transcription of the narration: spoken forms restored to canonical (`三百八十四` → `384`, `deepseek v4 flash vision exp` → `DeepSeek-V4-Flash-Vision-Exp`, "艾特" → `@`); commands, code, and versions verbatim (`pip install everos`, `rc.8`); sentence-final punctuation stripped (periods/commas/colons go, internal punctuation stays); over-length lines split at punctuation into more cues — never wrapped.
- **Narration track** (what TTS reads) is the speakable text: numbers spelled; symbols spelled (`node -v` → "node 减 v"); abbreviations letter-spaced when that reads better; English words written as words, never transliterated; star counts read as stars ("一万两千五百 stars"), never 颗星; compact codes (`0731`, `v0.1.1`) get their full spoken form plus one context anchor — bare codes are jargon. New proper nouns get a pronunciation probe with the user's ear before any full run (probe protocol and engine-side input traps live in tts-forge).

## Register

Pick the register at intake and hold it across the whole script. The production-proven default for news/explainer narration is **broadcast written style** — speakable written language, not chat: dates read 日 not 号; comparisons say 领先/落后, not 赢/输; internet-colloquial and childish words (随便用 / 摆在那 / 白送 / 不记事 / 塞回 / 排着队 / 跑起来 / 不吃亏) are rejected. For original narration this register overrides the AI-flavor gate's voice-preservation axis — there is no external author to preserve; on transcribed/translated material that axis keeps protecting the original speaker.

## Sentences

- Self-check by reading every sentence aloud at narration pace; anything a news anchor wouldn't say gets rewritten. Rejected fragment shapes, all from real rejections: bare-verb endings (今天讲清楚), four-character phrases standing as sentences (一个月，四连发), 了-ending chains, colloquial stubs (都能看了).
- Check the connections BETWEEN sentences — reference, logic, sequence — not just inside them.
- A sentence is broken when it has an unresolvable pronoun, an unrecoverable missing object, or an aspect-less verb ending.

## Openings and endings

- Openings: no series meta ("这是系列第一期"), no cross-episode callbacks as openers, no cold news-drop without setup. Proven shape: scale hook (a big real number) → what category this is → because (why it exists) → the data → today's topic. Start the first point directly — announcing the count first ("三条标准") is filler, on page titles too; production-process meta ("我快速过一遍") is cut as well. Product-update recaps stay — the test: about the product keeps, about our making of it gets cut.
- Endings: no farewell card, no catchphrase, no next-episode promise. The spoken close may summarize in plain words; the closing VISUAL is not the subtitle of that summary — it is the subject's own facts (logo, name, one data line), then hard cut.
- Breaking changes and renames are explained as "what it is + why it hurts you", never as version chronology.

## Terminology

- Terms stay terms, each with one plain-phrase explanation at first mention (灾难性遗忘——新的图文数据会持续修改原有权重，原本调校好的文本能力随之受损). Avoiding the term or sanding the script to 大白话 is the same defect as jargon-stacking; on-screen text follows the same rule as the narration.
- In series continuations, audience-known words (agent, plugin, token) pass without re-explanation; for a new audience, first-mention context does the work. Both are "term + context"; neither is downgrade.
- Proper nouns arrive where they matter ("MemOS 背后是向量数据库公司 Zilliz"), never cold in the opening.
- Product criticism states facts, not verdicts — "dsh 目前没有内置记忆功能", never "明显的短板" (a verdict reads as a hit-piece).
- Audience-known facts are not news — the news is the delta (agents having memory generally isn't the story; THIS tool lacking it is).
- Neutral vocabulary for investigative subjects (线索 / 印证 / 先例 / 谜面； not 嫌疑 / 惯犯 / 前科) unless the subject is an actual scandal.

## Density

Information-block count meets or beats the channel's previous video on the same topic: list that video's blocks, diff, then add new ones (first video on a topic: the bar is the material's own information value). Counterexample material found by our own search rather than the audience's need gets cut, not forced in; a conclusion sentence carrying no information is zero-value. Runtime is no ceiling — facts are selected by information value, never cut for length.

## The edit cascade (any script change after synthesis)

A text change is never one change. The full chain, every time: re-synthesize the changed cue (delete that segment's audio file so the resume-skip regenerates it — `--force` re-spends the whole run) → re-run forced alignment (timestamps/SRT/anchors rebuild) → re-derive the timing table (later scenes shift) → rebuild the master audio → clear `node_modules/.cache` and `out/segments/` (render-strategy rules, delivery.md) → re-render + frame-exact check → sync publish copy (chapters, numbers, wording) → sync the project's second script copy if it keeps one (a stale copy renders `relStart` of undefined). Scope is confirmed with the user BEFORE editing (Hard lines, SKILL.md).

## Cue length

Compute, never hardcode: `max chars = usable width ÷ font size` (CJK glyph width ≈ font size; Latin ≈ 0.6 × font size). The same font size fits different counts at different container widths. Over-length cues split at semantic points into more cues.

## Before the user sees the script

Run the Step 3 gates over it (terminology / AI-flavor / facts, materials.md), then this file's read-aloud self-check. A gate pass is not an ear pass — register-level slop survives pattern lists; the user's listen is final.
