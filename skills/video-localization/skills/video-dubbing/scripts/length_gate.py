"""Pre-synth length gate for the dub translation — pure arithmetic, no audio.

Reads transcript/<name>.en.full.srt (cue windows) + transcript/translations_dub.txt
(one Chinese line per cue) and flags, per cue:

  1. short-line trap: <= 8 syllables. IndexTTS2 renders standalone short
     lines at narration pace (observed ~2.6 syll/s; est_duration plans at
     ~3.0, rate_report's WARN boundary, vs 4.2-5.5 normal) — shorter is
     SLOWER. Rewrite fuller or let build_merge group it.
  2. budget miss: each cue's char budget is its window (cue start to the next
     cue's start — window + following pause). The identity assembler lands
     every cue's audio in that window with a per-cue atempo, so a factor far
     from 1.0 is not a frozen frame anymore — it is a sentence whose text is
     wrong for its window (factor > 1.5: audibly rushed after atempo, cut it
     back; factor < 0.6: seconds of dead air in the window, fill it).
  3. coverage total: sum of estimated speech / sum of windows. The per-line
     checks say nothing about the whole — a uniformly thin translation passes
     every line check and still dubs to long silences. Healthy band 90-105%;
     below 85% or above 112% fails.

Syllable counting: CJK chars 1:1, latin words by vowel groups — the metric all dub tools share.
Exit 0 = no short/must-fix lines and coverage in band (advisory-only runs
also exit 0); exit 1 = short, must-fix, or coverage out of band.

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
# (>20) at ~4.9. A single flat rate mis-estimates both ends. The plan rates
# need not match any specific voice exactly — whatever the synthesized audio
# actually does, the assembler's per-cue atempo absorbs the residual; these
# rates only have to be close enough to catch budget misses.
def est_duration(syl: int) -> float:
    if syl <= 8:
        return syl / 3.0
    if syl <= 20:
        return syl / 4.2
    return syl / 4.9

# Budget-miss bands on the per-cue factor est/window. 1.5 is where atempo
# starts sounding rushed; 0.6 leaves >40% of the window silent.
OVER_FACTOR = 1.5
UNDER_FACTOR = 0.6
# Coverage total: healthy 0.90-1.05, hard fail outside this band.
COVERAGE_MIN = 0.85
COVERAGE_MAX = 1.12
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
    # pause after each cue — part of that cue's window on the identity clock
    # (the assembler's window is cue start to next cue's start); 0 for the last
    gaps = [(spans[i + 1][0] - spans[i][1]) if i + 1 < len(spans) else 0.0
            for i in range(len(spans))]
    budgets = [w + g for w, g in zip(windows, gaps)]
    lines = [l.strip() for l in trans.read_text(encoding="utf-8").splitlines() if l.strip()]
    if len(windows) != len(lines):
        print(f"ERROR: {len(windows)} srt cues vs {len(lines)} translation lines — "
              "rerun after aligning (make_zh_dub_srt reports the same counts)")
        sys.exit(2)

    short, over, under = [], [], []
    total_est = total_budget = 0.0
    for i, (budget, zh) in enumerate(zip(budgets, lines), 1):
        syl = syllables(zh)
        est = est_duration(syl)
        total_est += est
        total_budget += budget
        if syl <= SHORT_SYLLS:
            short.append((i, syl, est, zh))
        if budget > 0:
            factor = est / budget
            if factor > OVER_FACTOR:
                over.append((i, factor, est, budget, zh))
            elif factor < UNDER_FACTOR:
                under.append((i, factor, budget, zh))

    coverage = total_est / total_budget if total_budget else 0.0

    if short:
        print(f"short-line trap (<= {SHORT_SYLLS} syllables, IndexTTS2 narration pace):")
        for i, syl, est, zh in short:
            print(f"  line {i}: {syl} sylls (~{est:.1f}s) | {zh[:40]}")
    if over:
        print(f"MUST FIX — over budget (est/window > {OVER_FACTOR}x; atempo will sound rushed):")
        for i, factor, est, budget, zh in over:
            print(f"  line {i}: {factor:.2f}x (~{est:.1f}s vs {budget:.1f}s window) | {zh[:40]}")
    if under:
        print(f"fill these — under budget (est/window < {UNDER_FACTOR}x; seconds of dead air):")
        for i, factor, budget, zh in under:
            print(f"  line {i}: {factor:.2f}x (window {budget:.1f}s) | {zh[:40]}")
    print(f"coverage: {total_est:.0f}s est / {total_budget:.0f}s windows = {coverage*100:.1f}% "
          f"(healthy 90-105%)")
    if coverage < COVERAGE_MIN:
        print(f"length gate FAIL: coverage {coverage*100:.0f}% < {COVERAGE_MIN*100:.0f}% — "
              "the translation is uniformly thin; every window gets dead air. Expand to the "
              "char budget (SKILL.md Step 3; REFERENCE.md 'Filling the char budget').")
        sys.exit(1)
    if coverage > COVERAGE_MAX:
        print(f"length gate FAIL: coverage {coverage*100:.0f}% > {COVERAGE_MAX*100:.0f}% — "
              "the whole script is over budget; trim filler, not content.")
        sys.exit(1)

    if not short and not over and not under:
        print(f"length gate PASS: {len(lines)} lines, coverage {coverage*100:.1f}%, "
              f"none under {SHORT_SYLLS} syllables")
        sys.exit(0)
    if short or over:
        print(f"length gate FAIL: {len(short)} short, {len(over)} over-budget — "
              "rewrite these lines, then rerun")
        sys.exit(1)
    print(f"length gate: advisory only ({len(under)} under-budget lines) — proceeding is "
          "reasonable; the assembler pads the shortfall with silence")
    sys.exit(0)


if __name__ == "__main__":
    main()
