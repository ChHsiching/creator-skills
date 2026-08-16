# Caption spec

The caption structure for Xiaohongshu, adapted from video-subtitle's `upload.md` character rules. The packaging differs (no video timestamps — use page numbers instead); the counting rules do not.

## Character limits (how the platform counts)

Every character counts, including spaces and punctuation. Verify with `len()` after writing; if over, compress.

| Field | Limit |
|---|---|
| Title | ≤ 20 characters |
| Body (笔记正文) | ≤ 100 characters |
| Pinned comment (置顶评论) | ≤ 300 characters, including spaces and newlines |

## caption.md structure

### Title (≤ 20 chars)

Multiple options. None duplicates the cover text (the cover already says the version/name). The title tells the viewer what the deck is about, in a professional tone — no marketing language ("大佬带你", "效率翻倍").

```python
titles = ["...", "..."]
for t in titles: assert len(t) <= 20
```

### Body (≤ 100 chars)

Multiple options, plain text (no markdown). This is the note's body field — short. Aim for the core hook: what changed, how many cards, why worth a look.

```python
bodies = ["...", "..."]
for b in bodies: assert len(b) <= 100
```

### Pinned comment (≤ 300 chars)

A compressed version of the body — the platform's pinned-comment slot, where the 300-char budget is precious. Include the substance (what changed, the notable items) and the source links at the end. No "看点" / "关键内容" sections — they waste the budget.

```python
pinned = "..."
assert len(pinned) <= 300
```

### Chapter list (two versions)

Corresponds to the cards. Two products, different rules:

- **Platform chapter field** (小红书 ≤ 15 entries): page label + short name (≤ 11 chars). Use `第NN张` instead of a timestamp (there is no video).
- **Pinned-comment chapter list** (full, detailed): page label + descriptive name (no length limit). This goes in a pinned comment, not the platform field — longer, clearer names are useful here.

### Image-note line (fixed wording)

Replaces video-subtitle's subtitle note. Use verbatim, adapted to the source:

> 图文：基于 `<author>` 公开发布的 `<source>` 整理制作。

### Hashtags

Vertical-domain terms (#AI编程 #ClaudeCode …) plus general traffic terms (#程序员 #技术分享). Match the deck's subject.

### Sources (separate section)

For readers who want to dig deeper — the original URL, the repo, the docs site, the release notes. Separate from the pinned comment (they would burn its 300-char budget).

## Verification

After writing caption.md, run the character-count check on every field. The run that produced this spec had a body draft at 101 chars (1 over) and a pinned comment at 355 chars (55 over) — both caught by `len()` and compressed before delivery. Always verify with `len()`.
