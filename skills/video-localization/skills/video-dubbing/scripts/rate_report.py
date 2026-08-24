"""Speech-rate report for the dub pipeline (post-synth audio gate).

IndexTTS2 renders standalone short lines at narration pace regardless of the
reference clip, and nothing else in the pipeline hears audio — this gate
catches it mechanically, right after synth, BEFORE the hours of retime+burn.

Per cue: rate = ZH syllables / audio duration. Buckets: short <=8 syl,
mid 9-20, long >20 (the model's own pacing bands). Verdict + per-cue
suggested fix factors follow the pacing policy:

    target = clamp(median rate of long cues — the mid bucket when the film
    has no long cues, else 4.2 — into 4.2..5.5)  # syll/s
    factor = min(1.6, target / rate)                     # only where rate < target

Usage:
    python rate_report.py <output-root> <name> [--json]

Reads: transcript/translations_dub.txt, dubbed/_full/timeline.json,
dubbed/_full/_segments/sent_NNNN.wav. Exit 0 = all buckets in band;
exit 1 = WARN condition below (agent should pause and report to the user).
"""
import argparse
import contextlib
import json
import re
import wave
from pathlib import Path

import numpy as np


def syllables(line: str) -> int:
    syl = len(re.findall(r"[\u4e00-\u9fff]", line))
    for w in re.findall(r"[A-Za-z]+", line):
        syl += max(1, len(re.findall(r"[aeiouAEIOU]+", w)))
    return syl


def wav_dur(p: Path) -> float:
    with contextlib.closing(wave.open(str(p), "rb")) as w:
        return w.getnframes() / w.getframerate()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output_root")
    ap.add_argument("name")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    root = Path(args.output_root)
    zh_lines = (root / "transcript" / "translations_dub.txt").read_text(
        encoding="utf-8").splitlines()
    tl = json.loads((root / "dubbed" / "_full" / "timeline.json").read_text(
        encoding="utf-8"))
    cue_idx = [s["idx"] for s in tl["timeline"] if s["kind"] == "cue"]
    assert len(cue_idx) == len(zh_lines), (len(cue_idx), len(zh_lines))

    rows = []
    for idx, zh in zip(cue_idx, zh_lines):
        wav = root / "dubbed" / "_full" / "_segments" / ("sent_%04d.wav" % idx)
        dur = wav_dur(wav)
        syl = syllables(zh)
        rate = syl / dur if dur > 0 else 0.0
        rows.append({"idx": idx, "syl": syl, "dur": round(dur, 2),
                     "rate": round(rate, 2), "zh": zh})

    def med(items):
        return round(float(np.median([r["rate"] for r in items])), 2) if items else None

    longs = [r for r in rows if r["syl"] > 20]
    mids = [r for r in rows if 9 <= r["syl"] <= 20]
    shorts = [r for r in rows if r["syl"] <= 8]
    # all-short films (pathological banter) have no longs/mids to anchor on:
    # fall back to the floor so the report still renders and WARNs
    film_normal = med(longs) or med(mids) or 4.2
    target = round(min(max(film_normal, 4.2), 5.5), 2)
    slow = []
    for r in rows:
        if r["rate"] < target:
            r["factor"] = round(min(1.6, target / r["rate"]), 2)
            slow.append(r)

    report = {
        "cues": len(rows),
        "buckets": {"short<=8": {"n": len(shorts), "median": med(shorts)},
                    "mid9-20": {"n": len(mids), "median": med(mids)},
                    "long>20": {"n": len(longs), "median": med(longs)}},
        "film_normal_median": film_normal,
        "policy_target": target,
        "slow_cues": len(slow),
        "slow": slow,
    }

    # WARN when the short bucket is pathological (model pacing bug) or the
    # whole film sits below the comfortable band.
    warn = (shorts and med(shorts) < 3.0) or (film_normal or 0) < 4.0

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
    else:
        print("buckets: short<=8 %s (n=%d, median %.2f) | mid9-20 (n=%d, median %.2f) | long>20 (n=%d, median %.2f)"
              % ("WARN" if shorts and med(shorts) < 3.0 else "ok",
                 len(shorts), med(shorts) or 0, len(mids), med(mids) or 0,
                 len(longs), med(longs) or 0))
        print("film normal median %.2f -> policy target %.2f | %d cues below target"
              % (film_normal or 0, target, len(slow)))
        for r in sorted(slow, key=lambda x: x["rate"])[:10]:
            print("  idx%d %.1f syll/s (factor %.2f) | %s" % (r["idx"], r["rate"], r["factor"], r["zh"][:24]))
        if len(slow) > 10:
            print("  ... and %d more" % (len(slow) - 10))
        print("VERDICT: %s" % ("WARN — pause and report to the user before retime/burn"
                               if warn else "PASS"))

    raise SystemExit(1 if warn else 0)


if __name__ == "__main__":
    main()
