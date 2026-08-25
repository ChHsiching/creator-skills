# Typography — the line-break discipline

Card text is mostly short, label-like fragments, not paragraphs. Every line break is therefore a **design decision you make**, per text block, at semantic points — matching the block's layout design. Dropping text into a container and letting `word-wrap` decide is the recurring defect behind orphan lines, split product names, and ragged half-empty blocks.

## The rules

1. **Break by semantics.** For any block longer than one line, place each line break where the meaning joints (phrase/clause boundary), so both lines read as designed units. A line 2 that exists only because one or two characters overflowed line 1 means the break is wrong — re-break the whole sentence semantically, or reword until it fits one line.
2. **Auto-wrap has one legitimate home**: genuine flowing paragraphs of 2+ lines (rare on cards — a caption strip, a quote). Everything else gets explicit breaks or fits one line.
3. **Proper nouns never split.** Product names, repo names, commands, URLs stay on one line — `whiteSpace: nowrap` on the element, or design the container wide enough. A name broken across lines is a defect the audit catches.
4. **Mono is for ASCII only.** Monospace stacks (JetBrains Mono etc.) carry no CJK glyphs; Chinese falls back to a system font mid-string and the mix looks broken. Chinese (or any non-Latin text) always renders in the body font; a mixed line splits into two elements (mono chip + body-font text).
5. **Fill the block.** A text block's lines should fill its width — if ink covers half the width, the breaks or the font size are wrong. Measure ink extent with a Range over the text node (`max right − min left`) against the container; a `div`'s bounding rect is the container, never the text.

## The typography review loop (Step 6)

A subagent reviews every card's rendered text against these five rules (feed it the screenshots plus, if needed, a DOM dump). It returns fail items as `{card, rule, quoted text, fix direction}`; you fix and re-review until clean. The loop is cheap; shipping a wrap defect to the user is not. The automated audit (verify.mjs) only catches a 1-character trailing line — a 2-character trailing line is legal when the break is semantic, so judging those is the loop's job.
