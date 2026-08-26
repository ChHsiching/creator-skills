"""Gap-absorbing timeline adjuster for the dub pipeline.

Problem: slow-rendered short cues stretch their video segments during retime
(ratio > 2x on interjections), making the whole video drag.

Fix: cap each cue segment's video stretch at --max-stretch; the Chinese audio
(never processed) overruns into the FOLLOWING gap instead. The next cue's
video segment starts no earlier than the previous audio end + --pad; to keep
the video tiling contiguous, the intervening segment (gap or cue) is extended
to cover the wait — a pause shot playing a bit longer, or a fallback stretch
when there is no gap at all.

Usage (between `cook dub timeline` and `cook dub retime`):

    python adjust_timeline.py <timeline.json> [--max-stretch 1.15]
        [--pad 0.08] [--first-cue-1x] [--force1x-file <idx-list>]

Rewrites timeline.json in place (backs up to timeline.pre-adjust.json —
refreshed every run: it always holds the state THIS run received).
Invariants (asserted): segments tile contiguously; strictly monotonic; cue
audio (duration zh_dur, glued to its segment start) never overlaps the next.
"""
import argparse
import json
import shutil
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("timeline_json")
    ap.add_argument("--max-stretch", type=float, default=1.15)
    ap.add_argument("--pad", type=float, default=0.08)
    ap.add_argument("--first-cue-1x", action="store_true",
                    help="first cue's video plays at exactly 1.0x (opening line: no stretch at all)")
    ap.add_argument("--force1x-file",
                    help="text file of cue idx values (one per line) whose video plays at exactly 1.0x")
    args = ap.parse_args()

    path = Path(args.timeline_json)
    data = json.loads(path.read_text(encoding="utf-8"))
    segs = data["timeline"]
    # Always snapshot the state THIS run received — in the rebuild loop
    # (timeline -> adjust -> audio fix -> timeline -> adjust ...) a
    # cycle-1 backup surviving into cycle 2 would restore zh_dur values
    # measured from wavs that no longer exist.
    shutil.copyfile(path, path.with_suffix(".pre-adjust.json"))

    force1x = set()
    if args.force1x_file:
        force1x = {int(x) for x in Path(args.force1x_file).read_text().split() if x.strip()}

    stats = {"capped": 0, "overrun_s": 0.0, "gap_extended_s": 0.0,
             "cue_fallback_s": 0.0, "sped_up": 0}

    clock = segs[0]["orig_start"]
    prev_audio_end = None
    for i, seg in enumerate(segs):
        start = clock
        if seg["kind"] == "cue":
            # Never start this cue's video/audio before the previous audio ends.
            if prev_audio_end is not None and start < prev_audio_end + args.pad:
                wait = prev_audio_end + args.pad - start
                start = prev_audio_end + args.pad
                prev = segs[i - 1]
                prev["new_end"] = round(start, 3)
                prev["new_dur"] = round(start - prev["new_start"], 3)
                # the extension changed prev's duration — its speed must
                # follow or the schema goes stale on exactly this path
                if prev["new_dur"] > 0:
                    prev["speed"] = round(
                        (prev["orig_end"] - prev["orig_start"]) / prev["new_dur"], 4)
                if prev["kind"] == "gap":
                    stats["gap_extended_s"] += wait
                else:
                    stats["cue_fallback_s"] += wait
            win = seg["orig_end"] - seg["orig_start"]
            zh = seg["zh_dur"]
            if zh > win:
                # prev_audio_end is None only before the first cue
                if seg["idx"] in force1x:
                    cap = 1.0
                elif args.first_cue_1x and prev_audio_end is None:
                    cap = 1.0
                else:
                    cap = args.max_stretch
                if zh <= win * cap + 1e-6:
                    dur = zh  # mild stretch, unchanged behavior
                else:
                    dur = win * cap  # cap; audio overruns into gaps
                    stats["capped"] += 1
                    stats["overrun_s"] += zh - dur
            else:
                dur = zh  # Chinese shorter: video speeds up (existing behavior)
                if zh < win - 1e-6:
                    stats["sped_up"] += 1
            prev_audio_end = start + zh
        else:
            dur = seg["orig_end"] - seg["orig_start"]  # 1:1 unless extended later
        seg["new_start"] = round(start, 3)
        seg["new_end"] = round(start + dur, 3)
        seg["new_dur"] = round(dur, 3)
        # keep `speed` honest for schema consumers: it is defined as
        # orig_dur / new_dur, so every re-timed segment (capped cue,
        # stretched gap, sped-up cue) must carry its new rate
        if dur > 0:
            seg["speed"] = round((seg["orig_end"] - seg["orig_start"]) / dur, 4)
        clock = seg["new_end"]

    data["total_new"] = segs[-1]["new_end"]
    data["adjust"] = {"max_stretch": args.max_stretch,
                      **{k: (round(v, 2) if isinstance(v, float) else v)
                         for k, v in stats.items()}}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    ok_tile = all(b["new_start"] == a["new_end"] for a, b in zip(segs, segs[1:]))
    cues = [s for s in segs if s["kind"] == "cue"]
    ok_audio = all(cues[i + 1]["new_start"] >= cues[i]["new_start"] + cues[i]["zh_dur"] - 1e-6
                   for i in range(len(cues) - 1))
    ok_mono = all(s["new_end"] > s["new_start"] for s in segs)
    print("capped %d cues (overrun %.1fs) | gap extended %.1fs | fallback stretch %.1fs | sped_up %d"
          % (stats["capped"], stats["overrun_s"], stats["gap_extended_s"],
             stats["cue_fallback_s"], stats["sped_up"]))
    print("total_new %.2fs | tiling %s | audio-no-overlap %s | monotonic %s"
          % (data["total_new"], ok_tile, ok_audio, ok_mono))

    # Freeze advisory: the gap-absorbing design assumes stretched pauses read
    # as natural hesitations — true around 1.2-2x, visibly a freeze beyond
    # ~3x (a 0.06s pause stretched 23x held for 1.4s on a shipped opening).
    # Name the extreme gaps so the translator can shorten the neighbouring
    # Chinese instead of shipping the freeze.
    deep = [(i, (s["orig_end"] - s["orig_start"]) / s["new_dur"])
            for i, s in enumerate(segs)
            if s["kind"] == "gap" and s["new_dur"] > 0
            and (s["orig_end"] - s["orig_start"]) / s["new_dur"] < 1 / 3]
    if deep:
        worst = min(r for _, r in deep)
        print("WARNING: %d gap(s) stretched >3x (worst %.1fx) — freeze-frame risk; "
              "consider shortening the Chinese of the neighbouring cues"
              % (len(deep), 1 / worst))

    assert ok_tile and ok_audio and ok_mono, "INVARIANT VIOLATION"


if __name__ == "__main__":
    main()
