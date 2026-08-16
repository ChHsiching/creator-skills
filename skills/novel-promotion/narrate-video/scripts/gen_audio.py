"""Sentence-level TTS for narrate-video skill.

Usage:
    python gen_audio.py <script.txt> <ref_voice.wav> <output_dir> [--tempo 1.15] [--emo-alpha 0.6] [--indextts-dir /path/to/index-tts]

Reads a script file, splits it into full sentences at 。！？, sends each
full sentence to IndexTTS2 in one call (IndexTTS2 reads internal commas
and pauses naturally), and records one timestamp per sentence.

Outputs:
    <output_dir>/audio.wav    — concatenated, speed-adjusted narration
    <output_dir>/audio.srt    — one cue per sentence (sentence-level timestamps)
"""
import argparse
import contextlib
import os
import re
import subprocess
import sys
import time
import wave


def split_sentences(text: str) -> list[str]:
    """Split at 。！？. Punctuation stays attached to the preceding sentence."""
    parts = re.split(r"(?<=[。！？])", text)
    return [p.strip() for p in parts if p.strip()]


def get_wav_duration(path):
    with contextlib.closing(wave.open(path, "rb")) as w:
        return w.getnframes() / float(w.getframerate())


def fmt_srt_time(seconds):
    ms_total = int(round(seconds * 1000))
    h, ms_total = divmod(ms_total, 3600000)
    m, ms_total = divmod(ms_total, 60000)
    s, ms = divmod(ms_total, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("script_path", help="path to script .txt file")
    p.add_argument("ref_voice", help="path to reference voice for cloning")
    p.add_argument("output_dir", help="where to write audio.wav + audio.srt")
    p.add_argument("--tempo", type=float, default=1.15,
                   help="playback speed multiplier (default 1.15)")
    p.add_argument("--emo-alpha", type=float, default=0.6,
                   help="emotion intensity 0-1 (default 0.6)")
    p.add_argument("--indextts-dir", required=True,
                   help="path to the index-tts installation (contains checkpoints/)")
    args = p.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    seg_dir = os.path.join(args.output_dir, "_segments")
    os.makedirs(seg_dir, exist_ok=True)

    # Read script
    with open(args.script_path, "r", encoding="utf-8") as f:
        script_text = f.read().strip()
    sentences = split_sentences(script_text)
    print(f"[1/4] script split into {len(sentences)} sentences:", flush=True)
    for i, s in enumerate(sentences):
        print(f"    {i:02d}: {s}", flush=True)

    # Load IndexTTS2 from the indextts install dir
    print(f"\n[2/4] loading IndexTTS2 from {args.indextts_dir}...", flush=True)
    sys.path.insert(0, args.indextts_dir)
    # force-reload in case a stale module is cached from another dir
    for mod in list(sys.modules):
        if mod.startswith("indextts"):
            del sys.modules[mod]
    from indextts.infer_v2 import IndexTTS2
    t0 = time.time()
    tts = IndexTTS2(
        cfg_path=os.path.join(args.indextts_dir, "checkpoints", "config.yaml"),
        model_dir=os.path.join(args.indextts_dir, "checkpoints"),
        use_fp16=False,
        use_cuda_kernel=False,
        use_deepspeed=False,
    )
    print(f"    loaded in {time.time()-t0:.1f}s", flush=True)

    # Synthesize each sentence
    print(f"\n[3/4] synthesizing {len(sentences)} sentences...", flush=True)
    seg_files = []
    for i, sent in enumerate(sentences):
        out = os.path.join(seg_dir, f"sent_{i:02d}.wav")
        if os.path.exists(out) and os.path.getsize(out) > 1000:
            dur = get_wav_duration(out)
            print(f"    sent {i:02d}: cached ({dur:.2f}s)  '{sent}'", flush=True)
            seg_files.append(out)
            continue
        t1 = time.time()
        tts.infer(
            spk_audio_prompt=args.ref_voice,
            text=sent,
            output_path=out,
            use_emo_text=True,
            emo_alpha=args.emo_alpha,
            use_random=False,
            verbose=False,
        )
        dur = get_wav_duration(out)
        print(f"    sent {i:02d}: {dur:.2f}s  ({time.time()-t1:.1f}s wall)  '{sent}'", flush=True)
        seg_files.append(out)

    # Concat with ffmpeg filter_complex
    print(f"\n[4/4] concatenating + speeding up {args.tempo}x...", flush=True)
    raw_concat = os.path.join(seg_dir, "_raw_concat.wav")
    inputs = []
    for sf in seg_files:
        inputs.extend(["-i", sf])
    n = len(seg_files)
    filter_str = "".join(f"[{i}:a]" for i in range(n)) + f"concat=n={n}:v=0:a=1[out]"
    subprocess.run(
        ["ffmpeg", "-y", *inputs,
         "-filter_complex", filter_str, "-map", "[out]",
         "-ar", "22050", "-ac", "1", raw_concat],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    out_audio = os.path.join(args.output_dir, "audio.wav")
    subprocess.run(
        ["ffmpeg", "-y", "-i", raw_concat,
         "-filter:a", f"atempo={args.tempo}",
         "-ar", "22050", "-ac", "1", out_audio],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    # Build SRT — one cue per sentence
    print(f"\nbuilding SRT (one cue per sentence)...", flush=True)
    srt_lines = []
    cursor = 0.0
    for i, sent in enumerate(sentences):
        raw_dur = get_wav_duration(seg_files[i])
        sped_dur = raw_dur / args.tempo
        start = cursor
        end = cursor + sped_dur
        srt_lines.append(f"{i + 1}")
        srt_lines.append(f"{fmt_srt_time(start)} --> {fmt_srt_time(end)}")
        srt_lines.append(sent)
        srt_lines.append("")
        cursor = end

    out_srt = os.path.join(args.output_dir, "audio.srt")
    with open(out_srt, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))

    total_dur = get_wav_duration(out_audio)
    print(f"\nDONE", flush=True)
    print(f"  sentences: {len(sentences)}", flush=True)
    print(f"  audio: {out_audio} ({total_dur:.2f}s, {os.path.getsize(out_audio)//1024}KB)", flush=True)
    print(f"  subtitle: {out_srt}", flush=True)


if __name__ == "__main__":
    main()
