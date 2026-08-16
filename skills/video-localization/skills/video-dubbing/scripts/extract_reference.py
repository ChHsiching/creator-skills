"""Extract a clean reference clip + its transcript for voice cloning.

Picks a 14-30s segment from separated vocals where the speaker is talking
steadily (high energy, low variance = no gaps/no overlaps), then transcribes
that segment with whisperX to produce ref.txt — the English transcript that
IndexTTS2 uses as its reference (the prompt whose timbre/prosody to clone).

Usage:
    python extract_reference.py <vocals.wav> <reference_dir>
        [--target-duration 16] [--min-duration 14] [--max-duration 30]
        [--whisper-model large-v3] [--language en]

Outputs:
    <reference_dir>/ref.wav    — the chosen 14-30s clip, 16kHz mono wav
    <reference_dir>/ref.txt    — the English transcript of ref.wav

The clip-selection heuristic: find the LONGEST continuous speech region (no
silence gaps > 0.3s) and cap it at max-duration. Long, connected regions
correlate with fast-paced speech without pauses — IndexTTS2 clones prosody
(rhythm/pacing), not just timbre, so a connected reference yields connected
Chinese.

If the user wants a specific clip instead (e.g. "use 01:23-01:31"), they can
skip this script and drop their own ref.wav + ref.txt into <reference_dir>/.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def get_duration(path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())


def detect_speech_regions(path: str) -> tuple[list[tuple[float, float]], float]:
    """Detect non-silent (speech) regions via ffmpeg silencedetect.
    Returns (regions, last_speech_end) where regions is a list of
    (start, end) spans of continuous speech, and last_speech_end is the
    end of the final detected silence (so the caller can append the
    tail region up to the file's total duration)."""
    r = subprocess.run(
        ["ffmpeg", "-i", path, "-af",
         f"silencedetect=noise=-40dB:d=0.3", "-f", "null", "-"],
        capture_output=True, text=True, check=True,
    )
    # Parse stderr for silence_start / silence_end events
    starts, ends = [], []
    for line in r.stderr.splitlines():
        if "silence_start" in line:
            starts.append(_parse_silence_time(line, "silence_start"))
        elif "silence_end" in line:
            ends.append(_parse_silence_time(line, "silence_end"))
    return _build_speech_regions(starts, ends)


def _parse_silence_time(line: str, marker: str) -> float:
    """'silence_start: 12.34' -> 12.34"""
    after = line.split(marker)[1].strip()
    # take leading float
    num = ""
    for ch in after:
        if ch.isdigit() or ch == ".":
            num += ch
        elif num:
            break
    return float(num) if num else 0.0


def _build_speech_regions(starts: list[float], ends: list[float]) -> list[tuple[float, float]]:
    """Convert silence events into speech regions (non-silent spans)."""
    # The first region: from 0 to the first silence_start (or to end if no silence)
    regions = []
    prev_end = 0.0
    for s_start, s_end in zip(starts, ends):
        if s_start > prev_end:
            regions.append((prev_end, s_start))
        prev_end = s_end
    # last region: from prev_end to end (added by caller with total duration)
    return regions, prev_end


def pick_best_clip(vocals_path: str, target_dur: float, min_dur: float,
                   max_dur: float) -> tuple[float, float]:
    """Find the best [start, end] window: the LONGEST continuous speech region
    available (capped at max_dur). Long regions correlate with connected,
    fast-paced speech without pauses — IndexTTS2 clones prosody, not just
    timbre, so a fast/connected reference yields fast/connected Chinese
    (A/B test: same sentence was 13.9s with a slow reference vs 4.0s with a
    connected one — 3.48x difference).

    Ties broken by earliness (intro/early segments tend to be cleaner takes).
    """
    total = get_duration(vocals_path)
    regions, last_speech_end = detect_speech_regions(vocals_path)
    if last_speech_end < total:
        regions.append((last_speech_end, total))

    # Filter to regions long enough
    candidates = [(s, e) for s, e in regions if e - s >= min_dur]
    if not candidates:
        # no clean region — fall back to a chunk from the middle
        mid = total / 2
        return (max(0, mid - target_dur / 2), min(total, mid + target_dur / 2))

    # Pick the longest region; break ties by earliest (intro is usually cleaner)
    candidates.sort(key=lambda r: (-(r[1] - r[0]), r[0]))
    best_start, best_end = candidates[0]

    # Cap at max_dur, keeping the start (earlier = cleaner take typically)
    if best_end - best_start > max_dur:
        best_end = best_start + max_dur
    return (best_start, best_end)


def transcribe_clip(clip_path: str, out_txt: str, model: str, language: str) -> None:
    """Transcribe the clip with whisperX. Uses the same model as video-subtitle
    (large-v3) so consistency is maintained."""
    # Try the video-subtitle skill's transcribe.py first (it handles caching,
    # alignment, etc). If not found, call whisperx directly.
    subtitle_script = _find_subtitle_script()
    if subtitle_script:
        tmp_srt = clip_path.replace(".wav", ".srt")
        subprocess.run(
            ["python", subtitle_script, clip_path, tmp_srt, model, "float32", language, "cpu"],
            check=True,
        )
        # Extract the text from the SRT (drop timestamps)
        _srt_to_text(tmp_srt, out_txt)
        os.remove(tmp_srt)
    else:
        # Direct whisperx fallback
        _whisperx_direct(clip_path, out_txt, model, language)


def _find_subtitle_script() -> str | None:
    """Look for video-subtitle's transcribe.py in sibling skill locations."""
    candidates = [
        os.path.expanduser("~/.agents/skills/video-subtitle/scripts/transcribe.py"),
        os.path.expanduser("~/.zcode/skills/video-subtitle/scripts/transcribe.py"),
    ]
    env = os.environ.get("VIDEO_SUBTITLE_SKILL_DIR")
    if env:
        candidates.insert(0, os.path.join(env, "scripts", "transcribe.py"))
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def _srt_to_text(srt_path: str, out_txt: str) -> None:
    """Pull just the text lines out of an SRT, joined by spaces."""
    import re
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()
    lines = []
    for block in content.strip().split("\n\n"):
        parts = block.strip().split("\n")
        if len(parts) >= 3:
            text = " ".join(parts[2:]).strip()
            text = re.sub(r"\s+", " ", text)
            if text:
                lines.append(text)
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(" ".join(lines).strip() + "\n")


def _whisperx_direct(clip_path: str, out_txt: str, model: str, language: str) -> None:
    import whisperx
    device = "cpu"
    compute_type = "float32"
    audio = whisperx.load_audio(clip_path)
    model_obj = whisperx.load_model(model, device, compute_type=compute_type, language=language)
    result = model_obj.transcribe(audio, batch_size=16, language=language)
    text = " ".join(seg["text"].strip() for seg in result["segments"])
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(text + "\n")


def main():
    p = argparse.ArgumentParser(
        description="Pick a clean reference clip + transcribe it for voice cloning."
    )
    p.add_argument("vocals_wav", help="path to separated vocals.wav (from cook dub separate)")
    p.add_argument("reference_dir", help="output dir for ref.wav + ref.txt")
    p.add_argument("--target-duration", type=float, default=16.0,
                   help="preferred clip length in seconds (default 16; IndexTTS2 recommends 14-30s)")
    p.add_argument("--min-duration", type=float, default=14.0,
                   help="minimum acceptable clip length (default 14; IndexTTS2 clones prosody and needs >=14s)")
    p.add_argument("--max-duration", type=float, default=30.0,
                   help="maximum clip length (default 30; matches IndexTTS2's documented upper bound)")
    p.add_argument("--whisper-model", default="large-v3",
                   help="whisperX model for the transcript (default large-v3)")
    p.add_argument("--language", default="en",
                   help="source language for transcription (default en)")
    args = p.parse_args()

    os.makedirs(args.reference_dir, exist_ok=True)
    ref_wav = os.path.join(args.reference_dir, "ref.wav")
    ref_txt = os.path.join(args.reference_dir, "ref.txt")

    # Pick the clip
    start, end = pick_best_clip(
        args.vocals_wav, args.target_duration, args.min_duration, args.max_duration
    )
    print(f"[1/3] picked clip {start:.2f}s - {end:.2f}s ({end-start:.2f}s)", flush=True)

    # Extract it as 16kHz mono wav with 0.5s silence padding at head and tail.
    # The tail padding guards against any reference-bleed into generated audio
    # (the last 100-200ms of the prompt can otherwise leak into the first
    # generated cue); the head padding gives the model a clean onset anchor.
    subprocess.run(
        ["ffmpeg", "-y", "-i", args.vocals_wav,
         "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
         "-af", "adelay=500|500,apad=pad_dur=0.5",
         "-ar", "16000", "-ac", "1", ref_wav],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    print(f"[2/3] wrote ref.wav ({get_duration(ref_wav):.2f}s)", flush=True)

    # Transcribe
    print(f"[3/3] transcribing with whisperX ({args.whisper_model})...", flush=True)
    transcribe_clip(ref_wav, ref_txt, args.whisper_model, args.language)
    with open(ref_txt, "r", encoding="utf-8") as f:
        transcript = f.read().strip()
    print(f"    ref.txt: '{transcript[:80]}{'...' if len(transcript) > 80 else ''}'", flush=True)
    print(f"\nDONE", flush=True)
    print(f"  ref.wav: {ref_wav}", flush=True)
    print(f"  ref.txt: {ref_txt}", flush=True)


if __name__ == "__main__":
    main()
