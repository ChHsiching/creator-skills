# Caption spec

## Character limits (the platform counts every character — spaces and punctuation included)

| Field | Limit | Target |
|---|---|---|
| Title | ≤ 20 | 14–18 |
| Body (笔记正文) | ≤ **1000** | write ~950, a full article — not a summary |
| Pinned comment | ≤ 300 | ~220 |

Count every field's characters (the platform counts spaces and punctuation) before delivery. Aim under the limits so edits don't push counts over (a run that iterated 1009→1003→1000→1011→991 spent five rounds learning this).

## Title — the cold-reader test

A viewer who has seen nothing but the title must know (a) what this is about and (b) what it does for them. Write benefit-first, in plain words; deck-internal vocabulary ("eli5", "神器", "那句话") is invisible to a cold reader — ban it from titles. Offer 2–3 options.

## Body — a full article (~950 chars)

The body is the note's actual text, not a teaser: a complete piece in news-brief register — what happened, the substance (commands, numbers, findings), what to do next. Chinese bullets use `·`. Close with the attribution line:

> 图文：基于 `<author>` 公开发布的 `<source>` 整理制作。

## Pinned comment (≤300)

Compressed substance + the deck map (第NN张 · name) + source URLs. No filler sections.

## Chapters (two versions)

- Platform field: ≤15 entries, `第NN张` + short name (≤11 chars).
- Pinned-comment version: full descriptive names, no length limit.

## Hashtags

Vertical terms (#AI编程 #ClaudeCode …) plus general traffic terms (#程序员 #技术分享), matched to the subject.

## Sources

Original URL, repo, docs — a separate section; they'd burn the pinned comment's budget.
