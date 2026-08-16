#!/usr/bin/env python3
"""SRT -> JSON for Remotion subtitle data. Also merges bilingual SRTs (zh + en cues
kept as separate fields per timestamp-union entry).

Why this exists: converting SRT by hand invites two session-proven bugs —
cue drift (count-only alignment checks pass while every line is off by one)
and bilingual-pair mis-splitting (which language is which line). This script
does it deterministically and verifies count + first/last timestamps.

Usage:
  # single SRT -> [{s, e, text}]
  python srt_to_json.py input.srt out.json
  # bilingual SRT (zh line above en line per cue) -> [{s, e, zh, en}]
  python srt_to_json.py --bilingual bilingual.srt out.json
"""
import argparse, json, re, sys


def ts(sec: str) -> float:
    h, m, rest = sec.split(":")
    return round(int(h) * 3600 + int(m) * 60 + float(rest.replace(",", ".")), 3)


def parse_blocks(raw: str):
    blocks = re.split(r"\n\n+", raw.strip())
    out = []
    for b in blocks:
        lines = b.split("\n")
        if len(lines) < 2:
            continue
        m = re.match(r"(\d\d:\d\d:\d\d[,.]\d+) --> (\d\d:\d\d:\d\d[,.]\d+)", lines[1])
        if not m:
            continue
        body = [l for l in lines[2:] if l.strip()]
        out.append((ts(m.group(1)), ts(m.group(2)), body))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--bilingual", action="store_true",
                    help="split each cue's body lines into zh (CJK-heavy) + en")
    args = ap.parse_args()

    blocks = parse_blocks(open(args.input, encoding="utf-8").read())
    result = []
    for s, e, body in blocks:
        if args.bilingual and len(body) >= 2:
            if re.search(r"[\u4e00-\u9fff]", body[0]):
                zh, en = body[0], body[1]
            else:
                zh, en = None, " ".join(body)
            result.append({"s": s, "e": e, "zh": zh, "en": en})
        else:
            text = " ".join(body)
            zh = text if re.search(r"[\u4e00-\u9fff]", text) else None
            en = None if zh else text
            result.append({"s": s, "e": e, "zh": zh, "en": en} if args.bilingual
                          else {"s": s, "e": e, "text": text})

    if not result:
        sys.exit("no cues parsed — check the input SRT")
    json.dump(result, open(args.output, "w", encoding="utf-8"), ensure_ascii=False)
    # verification summary — read it before handing the file to the renderer
    print(f"cues: {len(result)}  first: {result[0]['s']}s  last: {result[-1]['e']}s")
    if args.bilingual:
        zh_n = sum(1 for r in result if r.get("zh"))
        en_n = sum(1 for r in result if r.get("en"))
        print(f"with zh: {zh_n}  with en: {en_n}")
        if zh_n == 0 or en_n == 0:
            sys.exit("WARNING: one language is entirely missing — check the input pairing")


if __name__ == "__main__":
    main()
