"""Pre-synth length gate for the dub translation — pure arithmetic, no audio.

Reads transcript/<name>.en.full.srt (cue windows) + transcript/translations_dub.txt
(one Chinese line per cue) and flags, per cue:

  1. short-line trap: <= 8 syllables. IndexTTS2 renders standalone short
     lines at narration pace (observed ~2.6 syll/s; est_duration plans at
     ~3.0, rate_report's WARN boundary, vs 4.2-5.5 normal) — shorter is
     SLOWER. Rewrite fuller or let build_merge group it.
  2. over-length: estimated speech duration exceeds the cue's absorption
     budget (1.15x stretch + 90% of the following pause). The excess becomes
     a held frame — invisible below ~0.5s, a visible freeze beyond — so
     over-long Chinese is where freezes come from. Compress the
     translation here, not in retime.

Syllable counting matches rate_report.py so the two tools speak one metric.
Exit 0 = no short/must-fix lines (an advisory-only run also exits 0);
exit 1 = short or must-fix lines listed (fix them, rerun).

Usage: python length_gate.py <output_root> <name>
Run AFTER writing translations_dub.txt and BEFORE the Step 3 subagent
review, build_merge, and synth (it is cheap; the review is not).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Speech-rate PLANNING estimate, bucketed on rate_report's observed bands:
# short lines (<=8 sylls) plan at ~3.0 syll/s (observed narration pace ~2.6;
# 3.0 is rate_report's WARN boundary), mid at ~4.2 (observed ~4.3), long
# (>20) at ~4.9. A single flat rate mis-estimates both ends.
def est_duration(syl: int) -> float:
    if syl <= 8:
        return syl / 3.0
    if syl <= 20:
        return syl / 4.2
    return syl / 4.9
# Absorption budget, mirroring what adjust_timeline can actually do: stretch
# the cue's own video to 1.15x and bleed up to 90% of the following pause.
# Whatever the estimated speech exceeds THAT budget becomes a held frame —
# invisible at ~0.2s, a visible freeze beyond ~0.5s (the shipped 1.4s frozen
# opening lived here). Flag only lines whose required freeze is visible.
CUE_STRETCH = 1.15
GAP_USABLE = 0.9
# Freeze visibility bands. >2s is a must-fix wall of frozen picture (the
# shipped 1.4s opening was already objectionable); 0.5-2s reads as a slightly
# long pause — acceptable scattered, bad in clusters, so reported as a count
# for the translator's judgement rather than a wall of lines.
FREEZE_MUST_FIX = 2.0
FREEZE_VISIBLE = 0.5
# IndexTTS2's standalone short-line threshold (narration-pace trap).
SHORT_SYLLS = 8

_CUE_RE = re.compile(r"(\d+)\n([\d:,]+) --> ([\d:,]+)\n(.*?)\n", re.S)


def syllables(line: str) -> int:
    syl = len(re.findall(r"[\u4e00-\u9fff]", line))
    for w in re.findall(r"[A-Za-z]+", line):
        syl += max(1, len(re.findall(r"[aeiouAEIOU]+", w)))
    return syl


def sec(ts: str) -> float:
    h, m, rest = ts.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    root, name = Path(sys.argv[1]), sys.argv[2]
    full_srt = root / "transcript" / f"{name}.en.full.srt"
    trans = root / "transcript" / "translations_dub.txt"
    for f in (full_srt, trans):
        if not f.exists():
            print(f"ERROR: {f} not found")
            sys.exit(2)

    spans = []
    for m in _CUE_RE.finditer(full_srt.read_text(encoding="utf-8")):
        spans.append((sec(m.group(2)), sec(m.group(3))))
    windows = [e - s for s, e in spans]
    # pause available after each cue for overrun bleed (0 for the last cue)
    gaps = [(spans[i + 1][0] - spans[i][1]) if i + 1 < len(spans) else 0.0
            for i in range(len(spans))]
    lines = [l.strip() for l in trans.read_text(encoding="utf-8").splitlines() if l.strip()]
    if len(windows) != len(lines):
        print(f"ERROR: {len(windows)} srt cues vs {len(lines)} translation lines — "
              "rerun after aligning (make_zh_dub_srt reports the same counts)")
        sys.exit(2)

    short, must_fix, advisory = [], [], []
    for i, (win, gap, zh) in enumerate(zip(windows, gaps, lines), 1):
        syl = syllables(zh)
        est = est_duration(syl)
        budget = win * CUE_STRETCH + gap * GAP_USABLE
        freeze = est - budget
        if syl <= SHORT_SYLLS:
            short.append((i, syl, est, zh))
        if freeze > FREEZE_MUST_FIX:
            must_fix.append((i, freeze, est, budget, zh))
        elif freeze > FREEZE_VISIBLE:
            advisory.append((i, freeze))

    if short:
        print(f"short-line trap (<= {SHORT_SYLLS} syllables, IndexTTS2 narration pace):")
        for i, syl, est, zh in short:
            print(f"  line {i}: {syl} sylls (~{est:.1f}s) | {zh[:40]}")
    if must_fix:
        print(f"MUST FIX — freeze > {FREEZE_MUST_FIX}s after {CUE_STRETCH}x stretch "
              f"+ gap bleed:")
        for i, freeze, est, budget, zh in must_fix:
            print(f"  line {i}: +{freeze:.1f}s freeze (~{est:.1f}s vs {budget:.1f}s budget) | {zh[:40]}")
    if advisory:
        worst = max(f for _, f in advisory)
        print(f"advisory: {len(advisory)} line(s) with {FREEZE_VISIBLE}-{FREEZE_MUST_FIX}s "
              f"freeze risk (worst {worst:.1f}s) — tighten if clustered or at the opening")
    if not short and not must_fix and not advisory:
        print(f"length gate PASS: {len(lines)} lines, no freeze risk, "
              f"none under {SHORT_SYLLS} syllables")
        sys.exit(0)
    if short or must_fix:
        print(f"length gate FAIL: {len(short)} short, {len(must_fix)} must-fix — "
              "rewrite these lines, then rerun")
        sys.exit(1)
    print("length gate: advisory only (no must-fix, no short lines) — proceeding is "
          "reasonable, but the reported freezes will be visible on screen")
    sys.exit(0)


if __name__ == "__main__":
    main()
