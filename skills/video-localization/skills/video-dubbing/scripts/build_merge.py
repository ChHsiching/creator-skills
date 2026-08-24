"""Short-sentence merge planner for the dub pipeline.

IndexTTS2 renders standalone short lines (<=8 syllables) at narration pace
(~2.6 syll/s vs ~4.3 normal) regardless of the reference clip. Merging short
cues with neighbours into 9-24-syllable groups puts them in the model's
normal-pace band. Merged groups are re-synthesized as ONE audio unit (never
split back — the subtitle pipeline re-splits for display automatically).

IMPORTANT: merged groups must be synthesized with the SAME reference clip as
the reused audio, or the voice changes timbre mid-video.

Rules: a line is short when its ZH <= 8 syllables; merge with an adjacent
line when the inter-cue gap <= 1.5s and the group total stays <= 24 syllables
(<= 26 when absorbing a leading short into a following long line). Crossing
a longer pause would put one utterance across a moment that should be
silent; exceeding the band loses the normal-pace advantage.

Usage (before `cook dub synth`):
    python build_merge.py <output-root> <name>

Produces: merged en.full.srt + translations_dub.txt (backups as *.v1.*),
copies reusable v1 audio into dubbed/_full/_segments at the new indices
(merged groups left missing for `cook dub synth` to fill), and
transcript/merge_map.txt (new cue <- original line indices).
"""
import argparse
import re
import shutil
from pathlib import Path


def syllables(line: str) -> int:
    syl = len(re.findall(r"[\u4e00-\u9fff]", line))
    for w in re.findall(r"[A-Za-z]+", line):
        syl += max(1, len(re.findall(r"[aeiouAEIOU]+", w)))
    return syl


def fmt_ts(t: float) -> str:
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    ts = "%02d:%02d:%06.3f" % (h, m, s)
    return ts.replace(".", ",")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output_root")
    ap.add_argument("name")
    ap.add_argument("--max-gap", type=float, default=1.5,
                    help="max inter-cue pause to merge across (s)")
    ap.add_argument("--band-max", type=int, default=24,
                    help="max syllables in a merged group")
    args = ap.parse_args()

    root = Path(args.output_root)
    en_path = root / "transcript" / ("%s.en.full.srt" % args.name)
    zh_path = root / "transcript" / "translations_dub.txt"
    seg = root / "dubbed" / "_full" / "_segments"
    orig = root / "dubbed" / "_full" / "_segments_orig"

    cues = []
    for b in re.split(r"\n\s*\n", en_path.read_text(encoding="utf-8").strip()):
        lines = b.splitlines()
        if len(lines) < 3:
            continue
        m = re.match(r"(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)", lines[1])
        g = list(map(int, m.groups()))
        cues.append({"start": g[0]*3600+g[1]*60+g[2]+g[3]/1000,
                     "end": g[4]*3600+g[5]*60+g[6]+g[7]/1000,
                     "en": " ".join(l.strip() for l in lines[2:]),
                     "idx": int(lines[0])})
    zh_lines = zh_path.read_text(encoding="utf-8").splitlines()
    assert len(cues) == len(zh_lines), (len(cues), len(zh_lines))
    for c, z in zip(cues, zh_lines):
        c["zh"] = z
        c["syl"] = syllables(z)

    groups, cur = [], []
    for i, c in enumerate(cues):
        if not cur:
            cur = [i]
            continue
        total = sum(cues[j]["syl"] for j in cur)
        gap_ok = c["start"] - cues[cur[-1]]["end"] <= args.max_gap
        s = c["syl"]
        if s <= 8:
            if gap_ok and total + s <= args.band_max:
                cur.append(i)
            else:
                groups.append(cur)
                cur = [i]
        else:
            if total < 9 and gap_ok and total + s <= args.band_max + 2:
                cur.append(i)  # leading shorts + this line
            else:
                groups.append(cur)
                cur = [i]
    groups.append(cur)

    multi = [g for g in groups if len(g) > 1]
    merged_cues = sum(len(g) for g in multi)
    print("%d cues -> %d groups | %d merged groups absorb %d cues | solo %d"
          % (len(cues), len(groups), len(multi), merged_cues, len(groups) - len(multi)))

    for pth in [en_path, zh_path]:
        bak = pth.with_name(pth.name + ".v1")
        if not bak.exists():
            shutil.copyfile(pth, bak)

    en_out, zh_out = [], []
    for k, g in enumerate(groups, 1):
        first, last = cues[g[0]], cues[g[-1]]
        en_text = " ".join(cues[j]["en"] for j in g)
        zh_text = "".join(cues[j]["zh"] for j in g)
        en_out += [str(k), "%s --> %s" % (fmt_ts(first["start"]), fmt_ts(last["end"])), en_text, ""]
        zh_out.append(zh_text)
    en_path.write_text("\n".join(en_out), encoding="utf-8")
    zh_path.write_text("\n".join(zh_out) + "\n", encoding="utf-8")

    # Nothing else creates _segments_orig — if it's absent and the current
    # cache has wavs, THIS is the moment to snapshot them: the indices are
    # about to be renumbered, and without the snapshot the solo groups'
    # audio is unrecoverable (synth would re-synthesize everything, or
    # worse: a stale cache at the new indices silently mismatches).
    if not orig.exists() and any(seg.glob("sent_*.wav")):
        shutil.copytree(seg, orig)
        print("snapshotted existing audio cache -> %s" % orig.name)

    if not orig.exists():
        print("NOTE: no reusable audio found — nothing to pre-populate; "
              "cook dub synth will synthesize every group")
        return
    for f in seg.glob("sent_*.wav"):
        f.unlink()
    copied = 0
    for k, g in enumerate(groups, 1):
        if len(g) == 1:
            src = orig / ("sent_%04d.wav" % cues[g[0]]["idx"])
            shutil.copyfile(src, seg / ("sent_%04d.wav" % k))
            copied += 1
    print("audio pre-populated: %d copied / %d merged groups left for synth"
          % (copied, len(multi)))

    map_path = root / "transcript" / "merge_map.txt"
    map_path.write_text(
        "\n".join("%d <- %s" % (k, ",".join(str(cues[j]["idx"]) for j in g))
                  for k, g in enumerate(groups, 1)), encoding="utf-8")


if __name__ == "__main__":
    main()
