"""Convert SRT (one cue per full sentence) to ASS.

Subtitle display follows these rules (verbatim text — no punctuation added
or removed):

  1. Short sentence (fits on one line, <= MAX_CHARS_PER_LINE): show as-is.
  2. Long sentence WITHOUT internal punctuation: jieba semantic split into
     multiple visual lines.
  3. Long sentence WITH internal punctuation: first split at the punctuation
     (，；：). Then for each resulting fragment, if it still overflows the
     screen, apply jieba semantic split to that fragment alone. Fragments
     that already fit are left untouched.

All cues share the sentence's single timestamp range. \\N separates visual
lines within a cue. libass auto-wrap is disabled (WrapStyle=2).
"""
import sys
import re
from pathlib import Path

SRT_PATH = sys.argv[1] if len(sys.argv) > 1 else "subtitle_input.srt"
ASS_PATH = sys.argv[2] if len(sys.argv) > 2 else "subtitle_styled.ass"
# Use the font shipped with the skill (in fonts/ next to scripts/), not a
# hardcoded machine-specific path. Resolve relative to this script's location.
_SKILL_DIR = Path(__file__).resolve().parent.parent
FONT_PATH = str(_SKILL_DIR / "fonts" / "MicrosoftYaHeiBold.ttc")

PLAY_RES_X = 1080
PLAY_RES_Y = 1920
FONT_SIZE = 95
# At 95pt a CJK glyph renders ~95px wide. Screen is 1080, side margins 30px each
# -> 1020px usable. 1020 / 95 ≈ 10.7, so allow up to 11 chars (10 text + 1
# trailing punct) before a line overflows.
MAX_CHARS_PER_LINE = 11
MARGIN_L = 30
MARGIN_R = 30
MARGIN_V = 520  # distance from bottom — ~72% from top

# Strong end-of-sentence punctuation (splits the script into sentences)
SENTENCE_END = set("。！？")
# Weak punctuation inside a sentence (splits a sentence into fragments)
FRAG_END = set("，；：")
# All punctuation we treat as line-break candidates
ALL_PUNCT = SENTENCE_END | FRAG_END
# Single-char function words / particles that must never begin a line
GLUE = set("的了着地在上下和中或与及")

ASS_HEADER = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {PLAY_RES_X}
PlayResY: {PLAY_RES_Y}
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{FONT_PATH},{FONT_SIZE},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,6,2,2,{MARGIN_L},{MARGIN_R},{MARGIN_V},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def srt_time_to_ass(t: str) -> str:
    m = re.match(r"(\d+):(\d+):(\d+),(\d+)", t.strip())
    h, mn, s, ms = m.groups()
    return f"{int(h)}:{int(mn):02d}:{int(s):02d}.{int(ms)//10:02d}"


def jieba_split_to_lines(text: str, limit: int) -> list[str]:
    """Semantic-split `text` into lines of <=limit chars using jieba.

    Punctuation tokens (，。：) attach to the previous line and force a line
    break (acting as natural boundaries). Single-char function words
    (的/了/着/在) never start a line.
    """
    import jieba

    tokens = [t for t in jieba.cut(text) if t]
    lines = []
    buf = ""

    def flush():
        nonlocal buf
        if buf:
            lines.append(buf)
            buf = ""

    for tok in tokens:
        # Punctuation: attach to buf (or previous line), then flush.
        if tok in ALL_PUNCT and len(tok) == 1:
            if buf:
                buf += tok
                flush()
            elif lines:
                lines[-1] += tok
            continue

        # Glue particle: never start a line.
        if len(tok) == 1 and tok in GLUE and buf:
            buf += tok
            continue

        # Token longer than limit: hard-split at midpoint (last resort).
        while len(tok) > limit:
            flush()
            half = max(1, len(tok) // 2)
            if len(tok) - half <= 1:
                half = max(1, len(tok) - 2)
            lines.append(tok[:half])
            tok = tok[half:]
        if not tok:
            continue

        cand = buf + tok
        if len(cand) <= limit or not buf:
            buf = cand
        else:
            flush()
            buf = tok
    flush()
    return lines


def split_sentence_for_display(sentence: str, limit: int) -> str:
    """Apply the 3 rules to one sentence, return ASS text with \\N separators."""
    # Rule 1: short sentence fits on one line.
    if len(sentence) <= limit:
        return sentence

    # Check if sentence has any internal weak punctuation to split on.
    internal_punct = [c for c in FRAG_END if c in sentence]

    if not internal_punct:
        # Rule 2: long sentence WITHOUT punctuation -> jieba semantic split.
        lines = jieba_split_to_lines(sentence, limit)
        return "\\N".join(lines)

    # Rule 3: long sentence WITH punctuation -> split at punctuation first.
    parts = re.split(r"(?<=[，；：])", sentence)
    parts = [p for p in (s.strip() for s in parts) if p]

    final_lines = []
    for p in parts:
        if len(p) <= limit:
            # Fragment fits -> keep as-is.
            final_lines.append(p)
        else:
            # Fragment still overflows -> jieba semantic split THIS fragment.
            final_lines.extend(jieba_split_to_lines(p, limit))

    return "\\N".join(final_lines)


def main():
    text = Path(SRT_PATH).read_text(encoding="utf-8", errors="ignore").strip()
    blocks = re.split(r"\n\s*\n", text)

    out_lines = [ASS_HEADER]
    for blk in blocks:
        lines = [ln for ln in blk.splitlines() if ln.strip()]
        if len(lines) < 3:
            continue
        idx = 0
        if lines[0].strip().isdigit():
            idx = 1
        tc_line = lines[idx]
        text_line = "".join(lines[idx + 1:])
        if "->" not in tc_line:
            continue
        start_s, end_s = tc_line.split("-->")
        start = srt_time_to_ass(start_s)
        end = srt_time_to_ass(end_s)
        wrapped = split_sentence_for_display(text_line, MAX_CHARS_PER_LINE)
        out_lines.append(
            f"Dialogue: 0,{start},{end},Default,,0,0,0,,{wrapped}"
        )

    Path(ASS_PATH).write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print(f"wrote {ASS_PATH}")
    print(f"  font size: {FONT_SIZE}, outline: 6px")
    print(f"  max chars per line: {MAX_CHARS_PER_LINE}")
    print(f"  rules: short=as-is / long-no-punct=jieba / long-with-punct=punct+per-frag jieba")


if __name__ == "__main__":
    main()
