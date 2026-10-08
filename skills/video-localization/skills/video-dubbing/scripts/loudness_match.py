# -*- coding: utf-8 -*-
"""Per-cue loudness matching, run between synth and assemble.

The assembler's global loudnorm lands the TRACK at -18 LUFS but cannot fix
level spread BETWEEN voices — two clone references can sit 25 dB apart, and
every cue lands wherever its synthesis did. This script measures each
dubbed/_full/_segments/sent_NNNN.wav (ffmpeg ebur128, Summary block only) and
pulls it to the anchor with peak protection. Run it once after synth, before
`cook dub assemble` (assemble's fit pass overwrites segments in place).

Usage:
  python loudness_match.py <output-root> <name> [--anchor -18.7] [--peak -1.5]

Cues already within TOL of the anchor are skipped, so re-running is cheap.
"""
import argparse
import os
import re
import subprocess
import tempfile

TOL = 0.3  # LU — skip cues already this close to the anchor


def measure(path):
    """(integrated LUFS, true peak dB) — parse the Summary block ONLY: the
    progress lines carry a running I: that starts at -70 and mis-parses."""
    p = subprocess.run(
        ["ffmpeg", "-nostats", "-i", path,
         "-filter_complex", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True, text=True, errors="replace")
    summary = p.stderr.split("Summary:")[-1]
    m_i = re.search(r"I:\s*(-?[\d.]+)\s*LUFS", summary)
    m_p = re.search(r"Peak:\s*(-?[\d.]+)\s*dB(?:TP|FS)", summary)
    if not m_i or not m_p:
        raise RuntimeError(f"ebur128 parse fail: {path}")
    return float(m_i.group(1)), float(m_p.group(1))


def apply_gain(path, gain_db):
    d = os.path.dirname(path)
    with tempfile.NamedTemporaryFile(suffix=".wav", dir=d, delete=False) as f:
        tmp = f.name
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", path,
         "-af", f"volume={gain_db:.2f}dB", "-c:a", "pcm_s16le", tmp],
        capture_output=True, text=True)
    if r.returncode != 0:
        os.unlink(tmp)
        raise RuntimeError(r.stderr)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("output_root")
    ap.add_argument("name")
    ap.add_argument("--anchor", type=float, default=-18.7,
                    help="target integrated LUFS per cue (default -18.7)")
    ap.add_argument("--peak", type=float, default=-1.5,
                    help="true-peak ceiling in dBFS (default -1.5)")
    args = ap.parse_args()

    segs = os.path.join(args.output_root, "dubbed", "_full", "_segments")
    wavs = sorted(os.path.join(segs, f) for f in os.listdir(segs)
                  if re.fullmatch(r"sent_\d{4}\.wav", f))
    print(f"{len(wavs)} cue wavs; anchor {args.anchor} LUFS, "
          f"peak ceil {args.peak} dBFS")
    gains, clamped = [], 0
    for n, p in enumerate(wavs, 1):
        if os.path.getsize(p) <= 1000:
            print(f"SKIP broken {os.path.basename(p)} (<1KB)")
            continue
        lufs, peak = measure(p)
        gain = args.anchor - lufs
        if peak + gain > args.peak:
            gain = args.peak - peak
            clamped += 1
        if abs(gain) < TOL:
            continue
        apply_gain(p, gain)
        gains.append(gain)
        if n % 50 == 0 or n == len(wavs):
            print(f"  {n}/{len(wavs)} done (last gain {gain:+.1f} dB)", flush=True)
    if gains:
        import statistics as st
        print(f"applied to {len(gains)} cues: min {min(gains):+.1f} / "
              f"med {st.median(gains):+.1f} / max {max(gains):+.1f} dB; "
              f"peak-clamped {clamped}")
    else:
        print("nothing to do — all cues already at anchor")


if __name__ == "__main__":
    main()
