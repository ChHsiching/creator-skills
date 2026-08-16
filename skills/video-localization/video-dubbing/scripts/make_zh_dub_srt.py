"""Generate zh.dub.srt (dubbing subtitle) from en.full.srt timestamps +
translations_dub.txt. Timestamps are inherited from en.full.srt; the actual
TTS-based timeline is computed later by full_dub.py's timeline stage.

Usage:
    python make_zh_dub_srt.py <en.full.srt> <translations_dub.txt> <output.zh.dub.srt>
"""
import re
import sys
import argparse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("en_full_srt", help="Full-sentence English SRT (from make_full_srt.py)")
    parser.add_argument("translations", help="Dub translations file (one Chinese line per cue)")
    parser.add_argument("output", help="Output zh.dub.srt path")
    args = parser.parse_args()

    cue_re = re.compile(
        r"(\d+)\s*\n"
        r"(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*\n"
        r"(.*?)(?=\n\n|\n\d+\s*\n|\Z)",
        re.DOTALL,
    )
    with open(args.en_full_srt, encoding="utf-8") as f:
        cues = [
            (int(m[1]), m[2], m[3])
            for m in cue_re.finditer(f.read())
        ]

    with open(args.translations, encoding="utf-8") as f:
        zh = [l.rstrip("\n") for l in f if l.strip()]

    if len(cues) != len(zh):
        sys.exit(f"line count mismatch: en.full.srt has {len(cues)} cues, "
                 f"translations has {len(zh)} lines")

    lines = []
    for (idx, st, et), z in zip(cues, zh):
        lines.append(str(idx))
        lines.append(f"{st} --> {et}")
        lines.append(z)
        lines.append("")

    with open(args.output, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"wrote {args.output}: {len(cues)} cues")


if __name__ == "__main__":
    main()
