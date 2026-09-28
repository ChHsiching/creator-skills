"""Scan a vocal track for reference-clip candidate windows: fastest + densest.

IndexTTS2 clones prosody, not just timbre — the reference window's delivery
becomes the whole dub's delivery. A slow, deliberate window (what "longest
continuous speech" tends to pick) dubs the entire video at that pace. This
scanner ranks fixed-length windows by syllable rate during speech, filtered
for density and pause length, and cuts the top candidates as wavs.

Usage:
  # scan + cut candidates (run under the IndexTTS2 venv — whisper scores)
  python scan_reference.py <audio.wav> --out <dir> [--win 15.0] [--top 3]
                          [--min-density 0.85] [--max-gap 1.0] [--full-band <video.mp4>]

  <audio.wav>    16kHz mono vocal track (Demucs vocals or clean original)
  --win          window length in seconds. IndexTTS2 reads at most the first
                 15s of a reference — the default uses the full cap.
  --full-band    optionally also cut the same windows from a full-band source
                 (the original video file) at 48kHz, higher fidelity than the
                 16k scan track.

  # score synthesized takes against the speaker's REAL voice (optional)
  python scan_reference.py --score <take1.wav> [take2.wav ...] --anchor <anchor.wav>

  --score compares each take's speaker embedding to <anchor.wav> (any real
  clip of the speaker). Comparing takes to the ANCHOR, not to the reference
  clip itself, is what makes the number meaningful: similarity to the
  reference is guaranteed by construction, similarity to the speaker is the
  thing you are choosing. Higher cosine wins.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import wave
from pathlib import Path


def syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    return max(1, len(re.findall(r"[aeiouy]+", w))) if w else 0


def wav_dur(p: Path) -> float:
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


def transcribe_words(audio: Path, cache: Path) -> list[dict]:
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    from faster_whisper import WhisperModel
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(audio), language="en", word_timestamps=True,
                                   vad_filter=False, beam_size=1)
    words = []
    for seg in segments:
        for w in seg.words or []:
            if w.word.strip():
                words.append({"s": w.start, "e": w.end, "t": w.word.strip()})
    cache.write_text(json.dumps(words), encoding="utf-8")
    return words


def scan(words: list[dict], dur: float, win: float, step: float,
         min_density: float, max_gap: float) -> list[dict]:
    for w in words:
        w["syll"] = syllables(w["t"])
    out = []
    t = 0.0
    while t + win <= dur:
        ws = [w for w in words if w["s"] >= t and w["e"] <= t + win]
        if ws:
            speech = sum(w["e"] - w["s"] for w in ws)
            density = speech / win
            gaps = [b["s"] - a["e"] for a, b in zip(ws, ws[1:])]
            max_gap = max(gaps) if gaps else 0.0
            if density >= min_density and max_gap <= max_gap:
                out.append({
                    "t0": round(t, 2), "t1": round(t + win, 2),
                    "syll_rate": round(sum(w["syll"] for w in ws) / win, 2),
                    "density": round(density, 3),
                    "max_gap": round(max_gap, 2),
                })
        t += step
    out.sort(key=lambda r: -r["syll_rate"])
    return out


def cut(src: Path, t0: float, t1: float, dst: Path, rate: int) -> None:
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(t0), "-to", str(t1),
                    "-i", str(src), "-vn", "-c:a", "pcm_s16le", "-ar", str(rate),
                    "-ac", "1", str(dst)], check=True)


def score(anchor: Path, takes: list[Path]) -> None:
    """Cosine similarity of speaker embeddings (IndexTTS2's CAMPPlus path)."""
    import torch
    import torchaudio

    def style(tts, wav_path: Path):
        audio, sr = torchaudio.load(str(wav_path))
        if audio.shape[0] > 1:
            audio = audio.mean(0, keepdim=True)
        if sr != 16000:
            audio = torchaudio.transforms.Resample(sr, 16000)(audio)
        feat = torchaudio.compliance.kaldi.fbank(
            audio, num_mel_bins=80, dither=0, sample_frequency=16000)
        feat = feat - feat.mean(dim=0, keepdim=True)
        return tts.campplus_model(feat.unsqueeze(0))

    indextts_dir = Path(__import__("os").environ.get(
        "INDEXTTS_DIR", Path.home() / "Git" / "index-tts"))
    sys.path.insert(0, str(indextts_dir))
    from indextts.infer_v2_5 import IndexTTS2
    tts = IndexTTS2(
        cfg_path=str(indextts_dir / "checkpoints" / "config.yaml"),
        model_dir=str(indextts_dir / "checkpoints"),
        use_bf16=False, use_cuda_kernel=False, use_deepspeed=False, device="cpu",
        use_qwen_emo=False,
    )
    ref_style = style(tts, anchor)
    for t in takes:
        s = style(tts, t)
        cos = float(torch.nn.functional.cosine_similarity(ref_style, s, dim=1))
        print(f"{cos:.4f}  {t}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("audio", nargs="?", help="16kHz mono vocal track to scan")
    ap.add_argument("--out", help="directory to cut candidate wavs into")
    ap.add_argument("--win", type=float, default=15.0)
    ap.add_argument("--step", type=float, default=0.5)
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--min-density", type=float, default=0.85)
    ap.add_argument("--max-gap", type=float, default=1.0)
    ap.add_argument("--full-band", help="full-band source (e.g. the raw mp4) to also cut from")
    ap.add_argument("--score", nargs="+", metavar="TAKE",
                    help="score these takes against ANCHOR instead of scanning")
    ap.add_argument("--anchor", type=Path, help="anchor wav for --score (speaker's real voice)")
    args = ap.parse_args()

    if args.score:
        if not args.anchor:
            ap.error("--score needs --anchor")
        score(args.anchor, [Path(t) for t in args.score])
        return
    if not args.audio or not args.out:
        ap.print_help()
        sys.exit(2)

    audio = Path(args.audio)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    dur = wav_dur(audio)
    print(f"{audio.name}: {dur:.1f}s; scanning {args.win:.1f}s windows "
          f"(density>={args.min_density}, gap<={args.max_gap})")
    words = transcribe_words(audio, out_dir / "_scan_words.json")
    ranked = scan(words, dur, args.win, args.step, args.min_density, args.max_gap)
    (out_dir / "_scan_windows.json").write_text(json.dumps(ranked[:50], indent=1),
                                                encoding="utf-8")
    if not ranked:
        print("no window passed the filters — relax --min-density/--max-gap")
        sys.exit(1)
    for i, r in enumerate(ranked[:args.top], 1):
        dst = out_dir / f"cand{i}.wav"
        cut(audio, r["t0"], r["t1"], dst, 16000)
        print(f"cand{i}: {r['t0']}-{r['t1']} rate={r['syll_rate']} "
              f"density={r['density']} gap={r['max_gap']} -> {dst}")
        if args.full_band:
            fb = out_dir / f"cand{i}_48k.wav"
            cut(Path(args.full_band), r["t0"], r["t1"], fb, 48000)
            print(f"       full-band -> {fb}")
    print("hand the candidates to the ear gate (SKILL.md Step 3a): synth the pilot "
          "sentences with each, score takes with --score --anchor <real clip>, "
          "then the user picks by ear.")


if __name__ == "__main__":
    main()
