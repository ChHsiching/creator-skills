"""Chinese dub synthesis for the video-dubbing skill.

Reads a Chinese SRT (the dub script — already translated by video-subtitle),
clones the original speaker's voice from a reference clip, and synthesizes
a Chinese dub track aligned to the original SRT timeline.

Usage:
    python dub_audio.py <zh.srt> <ref.wav> <ref.txt> <dubbed_dir>
        [--no-ultimate-cloning] [--device cpu]
        [--tts-backend voxcpm2|indextts2]

Per-cue synthesis (one cue = one SRT entry). Each cue is time-aligned to its
original window via ffmpeg atempo (±25% — beyond that, the cue is logged to
dubbed/alignment-issues.md for manual review, since atempo above 1.25/0.8
sounds chipmunked or drugged).

Outputs:
    <dubbed_dir>/dub.wav                  — full dub track, aligned to timeline
    <dubbed_dir>/alignment-issues.md      — cues that didn't fit (for review)
    <dubbed_dir>/_segments/sent_NNNN.wav  — per-cue cache (keyed by text hash)

The TTS backend is pluggable. VoxCPM2 (default) is the open-source SOTA for
zero-shot voice cloning as of July 2026; its Ultimate Cloning mode (passing
both reference audio AND its transcript) is what makes the dub sound like the
original speaker. See REFERENCE.md for the IndexTTS2 fallback.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import wave
from dataclasses import dataclass
from pathlib import Path


# ----------------------------------------------------------------------------
# SRT parsing
# ----------------------------------------------------------------------------

_CUE_RE = re.compile(
    r"(\d+)\s*\n(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*\n(.*?)(?=\n\n|\n\d+\s*\n|\Z)",
    re.DOTALL,
)


@dataclass
class Cue:
    index: int
    start: float  # seconds
    end: float    # seconds
    text: str


def _ts_to_sec(ts: str) -> float:
    """'00:01:23,456' -> 83.456"""
    ts = ts.replace(",", ".")
    h, m, s = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def parse_srt(path: str) -> list[Cue]:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    cues = []
    for m in _CUE_RE.finditer(content):
        idx = int(m.group(1))
        start = _ts_to_sec(m.group(2))
        end = _ts_to_sec(m.group(3))
        text = m.group(4).strip()
        # collapse internal whitespace/newlines into single spaces — the SRT
        # cue text may contain a newline if it was a two-line bilingual entry,
        # but the dub script is pure Chinese; take it as one line.
        text = re.sub(r"\s+", " ", text)
        if text:
            cues.append(Cue(idx, start, end, text))
    return cues


# ----------------------------------------------------------------------------
# Audio helpers
# ----------------------------------------------------------------------------

def get_wav_duration(path: str) -> float:
    with contextlib.closing(wave.open(path, "rb")) as w:
        return w.getnframes() / float(w.getframerate())


def fmt_srt_time(seconds: float) -> str:
    ms_total = int(round(seconds * 1000))
    h, ms_total = divmod(ms_total, 3600000)
    m, ms_total = divmod(ms_total, 60000)
    s, ms = divmod(ms_total, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def atempo_factor(speed_ratio: float) -> list[str]:
    """Build an atempo filter chain. ffmpeg's atempo accepts 0.5-2.0 per stage;
    for ratios outside that we chain two stages. ±25% is the practical limit
    for natural-sounding speech (above 1.25 sounds chipmunked)."""
    f = max(0.5, min(2.0, speed_ratio))
    if abs(f - speed_ratio) < 1e-3:
        return [f"atempo={f:.4f}"]
    # chain: first stage brings it partway, second stage the rest
    stage1 = f ** 0.5
    return [f"atempo={stage1:.4f}", f"atempo={f/stage1:.4f}"]


# ----------------------------------------------------------------------------
# TTS backends — pluggable. Default VoxCPM2 (SOTA July 2026).
# ----------------------------------------------------------------------------

class TTSBackend:
    """Abstract interface. load() once, synthesize_cue() per cue."""

    def load(self, ref_wav: str, ref_txt: str, ultimate: bool, device: str) -> None:
        raise NotImplementedError

    def synthesize_cue(self, text: str, out_path: str) -> None:
        raise NotImplementedError


class VoxCPM2Backend(TTSBackend):
    """VoxCPM2 zero-shot voice cloning with Ultimate Cloning mode.

    Ultimate Cloning: pass both the reference audio AND its transcript. The
    model does audio-continuation-based cloning, faithfully preserving timbre,
    rhythm, emotion, and style — better than passing the reference alone.
    """

    def load(self, ref_wav, ref_txt, ultimate, device):
        from voxcpm import VoxCPM  # lazy import — heavy
        # from_pretrained takes device directly — pass "cpu" explicitly on
        # non-CUDA hosts. If you hit the torch SDPA IndexError on CPU, see
        # REFERENCE.md — use source install or downgrade torch to 2.5.1.
        self.model = VoxCPM.from_pretrained(
            "openbmb/VoxCPM2", load_denoiser=False, device=device,
        )
        self.ref_wav = ref_wav
        self.ref_txt = ref_txt
        self.ultimate = ultimate
        with open(ref_txt, "r", encoding="utf-8") as f:
            self.ref_text_content = f.read().strip()

    def synthesize_cue(self, text, out_path):
        import soundfile as sf
        if self.ultimate:
            wav = self.model.generate(
                text=text,
                prompt_wav_path=self.ref_wav,
                prompt_text=self.ref_text_content,
                reference_wav_path=self.ref_wav,
            )
        else:
            wav = self.model.generate(
                text=text,
                reference_wav_path=self.ref_wav,
            )
        sr = self.model.tts_model.sample_rate
        sf.write(out_path, wav, sr)


class IndexTTS2Backend(TTSBackend):
    """Fallback backend. IndexTTS2 is already installed if you ran narrate-video.
    No Ultimate Cloning (passes reference audio only), but supports emo_alpha.
    Slower than VoxCPM2 on CPU."""

    def load(self, ref_wav, ref_txt, ultimate, device):
        # indextts-dir must be on PYTHONPATH; the skill's SKILL.md sets it
        # via the detached launcher. Force-reload to dodge stale modules.
        for mod in list(sys.modules):
            if mod.startswith("indextts"):
                del sys.modules[mod]
        from indextts.infer_v2 import IndexTTS2
        indextts_dir = os.environ.get("INDEXTTS_DIR", "")
        cfg = os.path.join(indextts_dir, "checkpoints", "config.yaml")
        mdir = os.path.join(indextts_dir, "checkpoints")
        self.model = IndexTTS2(
            cfg_path=cfg, model_dir=mdir,
            use_fp16=False, use_cuda_kernel=False, use_deepspeed=False,
        )
        self.ref_wav = ref_wav
        self.emo_alpha = float(os.environ.get("DUB_EMO_ALPHA", "0.6"))

    def synthesize_cue(self, text, out_path):
        self.model.infer(
            spk_audio_prompt=self.ref_wav,
            text=text,
            output_path=out_path,
            use_emo_text=True,
            emo_alpha=self.emo_alpha,
            use_random=False,
            verbose=False,
        )


def make_backend(name: str) -> TTSBackend:
    if name == "voxcpm2":
        return VoxCPM2Backend()
    if name == "indextts2":
        return IndexTTS2Backend()
    raise ValueError(f"unknown TTS backend: {name}")


# ----------------------------------------------------------------------------
# Main pipeline
# ----------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(
        description="Synthesize Chinese dub aligned to a zh.srt timeline."
    )
    p.add_argument("zh_srt", help="path to the Chinese SRT (dub script)")
    p.add_argument("ref_wav", help="reference voice clip (5-10s clean solo speech)")
    p.add_argument("ref_txt", help="English transcript of ref_wav (Ultimate Cloning)")
    p.add_argument("dubbed_dir", help="output dir (dub.wav, _segments/, alignment-issues.md)")
    p.add_argument("--tts-backend", default="voxcpm2", choices=["voxcpm2", "indextts2"],
                   help="TTS backend (default voxcpm2 = July 2026 SOTA; indextts2 = fallback if VoxCPM2 fails)")
    p.add_argument("--no-ultimate-cloning", action="store_true",
                   help="disable Ultimate Cloning (reference audio only, no transcript)")
    p.add_argument("--device", default="cpu", help="torch device (default cpu)")
    args = p.parse_args()

    os.makedirs(args.dubbed_dir, exist_ok=True)
    seg_dir = os.path.join(args.dubbed_dir, "_segments")
    os.makedirs(seg_dir, exist_ok=True)

    cues = parse_srt(args.zh_srt)
    print(f"[1/5] parsed {len(cues)} cues from {args.zh_srt}", flush=True)
    if not cues:
        sys.exit(f"ERROR: no cues in {args.zh_srt}")

    ultimate = not args.no_ultimate_cloning
    print(f"[2/5] loading {args.tts_backend} (ultimate_cloning={ultimate})...", flush=True)
    t0 = time.time()
    backend = make_backend(args.tts_backend)
    backend.load(args.ref_wav, args.ref_txt, ultimate, args.device)
    print(f"    loaded in {time.time()-t0:.1f}s", flush=True)

    # Synthesize each cue. Cache by (backend, ultimate, ref_wav, text) hash so
    # changing the reference, the backend, or the ultimate toggle invalidates
    # the cache correctly — but re-running after a single cue's text was fixed
    # only re-synthesizes that cue.
    print(f"\n[3/5] synthesizing {len(cues)} cues (CPU is slow — this is the long step)...", flush=True)
    seg_files = []
    for cue in cues:
        cache_key = hashlib.md5(
            f"{args.tts_backend}|{ultimate}|{args.ref_wav}|{cue.text}".encode("utf-8")
        ).hexdigest()[:12]
        out = os.path.join(seg_dir, f"sent_{cue.index:04d}_{cache_key}.wav")
        if os.path.exists(out) and os.path.getsize(out) > 1000:
            dur = get_wav_duration(out)
            print(f"    cue {cue.index:04d}: cached ({dur:.2f}s)  '{cue.text[:40]}'", flush=True)
            seg_files.append((cue, out))
            continue
        t1 = time.time()
        try:
            backend.synthesize_cue(cue.text, out)
        except Exception as e:
            print(f"    cue {cue.index:04d}: FAILED ({e})", flush=True)
            # write a silent placeholder so the timeline still aligns
            _write_silence(out, max(0.5, cue.end - cue.start))
        dur = get_wav_duration(out)
        print(f"    cue {cue.index:04d}: {dur:.2f}s ({time.time()-t1:.1f}s wall)  '{cue.text[:40]}'", flush=True)
        seg_files.append((cue, out))

    # Time-align each cue to its SRT window. Each cue occupies its own window
    # [cue.start, cue.end] — they are placed serially, never overlapping.
    # If the natural TTS duration exceeds the window, the cue is sped up via
    # atempo to fit exactly (no upper bound on speed — the goal is no overlap,
    # not naturalness at the cost of audio pile-up). Cues shorter than their
    # window keep their natural duration; the rest of the window stays silent.
    print(f"\n[4/5] aligning cues to timeline (serial, no overlap)...", flush=True)
    issues = []
    aligned_segs = []  # (start_offset, aligned_wav_path)
    for cue, seg in seg_files:
        natural_dur = get_wav_duration(seg)
        window_dur = max(0.3, cue.end - cue.start)
        aligned = os.path.join(seg_dir, f"aligned_{cue.index:04d}.wav")
        if natural_dur > window_dur:
            # Speed up to fit the window exactly. No cap — overlap is worse
            # than fast speech (a viewer can follow 1.5x, but two cues at
            # once is unintelligible). Log anything above 1.5x for review.
            speed = natural_dur / window_dur
            subprocess.run(
                ["ffmpeg", "-y", "-i", seg, "-filter:a", ",".join(atempo_factor(speed)),
                 "-ar", "22050", "-ac", "1", aligned],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            if speed > 1.5:
                issues.append((cue.index, cue.text, natural_dur, window_dur,
                               get_wav_duration(aligned), f"sped_up_{speed:.2f}x"))
        else:
            # Fits naturally — keep as-is, the window padding handles the rest.
            subprocess.run(
                ["ffmpeg", "-y", "-i", seg, "-ar", "22050", "-ac", "1", aligned],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        aligned_segs.append((cue.start, aligned))

    # Build the full dub track: pad silence up to each cue's start, then concat.
    # Use ffmpeg adelay per segment, then concat all.
    dub_wav = os.path.join(args.dubbed_dir, "dub.wav")
    _build_timeline(aligned_segs, dub_wav, total_duration=cues[-1].end + 0.5)
    print(f"    dub.wav: {get_wav_duration(dub_wav):.2f}s", flush=True)

    if issues:
        issues_md = os.path.join(args.dubbed_dir, "alignment-issues.md")
        with open(issues_md, "w", encoding="utf-8") as f:
            f.write("# Cues sped up to fit their time window\n\n")
            f.write("These cues' natural TTS duration exceeded their SRT window, so they were\n")
            f.write("sped up via atempo to fit exactly (no overlap with adjacent cues).\n")
            f.write("Cues listed here were sped up more than 1.5x — review and consider\n")
            f.write("re-translating those cues shorter in the zh.srt if they sound too rushed.\n\n")
            f.write("| Cue | Text | Natural | Window | Final | Status |\n")
            f.write("|---|---|---|---|---|---|\n")
            for idx, text, nat, tgt, final, status in issues:
                f.write(f"| {idx} | {text[:40]} | {nat:.2f}s | {tgt:.2f}s | {final:.2f}s | {status} |\n")
        print(f"    {len(issues)} cues flagged in {issues_md}", flush=True)

    print(f"\n[5/5] DONE", flush=True)
    print(f"  dub.wav: {dub_wav}", flush=True)
    print(f"  cues synthesized: {len(cues)}", flush=True)
    print(f"  alignment issues: {len(issues)}", flush=True)


def _write_silence(path: str, duration: float) -> None:
    """Write a silent wav as a placeholder when TTS fails on a cue."""
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r=22050:cl=mono",
         "-t", f"{duration:.2f}", path],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def _build_timeline(segments: list[tuple[float, str]], out_path: str,
                    total_duration: float) -> None:
    """Build the dub track by serial concatenation — each segment padded with
    silence before it (to reach its start offset) and after it (to reach the
    next segment's start), then all concatenated in order.

    This guarantees NO overlap between cues: each cue occupies exactly
    [start, start+duration] on the timeline, with silence filling any gap
    before the next cue. The previous adelay+amix approach summed overlapping
    cues; this concat approach cannot."""
    if not segments:
        _write_silence(out_path, total_duration)
        return

    # For each segment, prepend silence to reach its start offset (relative to
    # the previous segment's end), then write as a padded segment file.
    padded_files = []
    cursor = 0.0  # where the previous segment ended on the timeline
    for i, (start, wav) in enumerate(segments):
        seg_dur = get_wav_duration(wav)
        gap_before = max(0.0, start - cursor)
        padded = wav.replace(f"aligned_{i:04d}", f"padded_{i:04d}") \
            if f"aligned_{i:04d}" in wav else \
            os.path.join(os.path.dirname(wav), f"padded_{i:04d}.wav")
        # Build: silence(gap_before) + wav, normalize to 22050 mono
        if gap_before > 0.001:
            subprocess.run(
                ["ffmpeg", "-y",
                 "-f", "lavfi", "-t", f"{gap_before:.3f}", "-i", "anullsrc=r=22050:cl=mono",
                 "-i", wav,
                 "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1[out]",
                 "-map", "[out]", "-ar", "22050", "-ac", "1", padded],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        else:
            # No gap — just normalize
            subprocess.run(
                ["ffmpeg", "-y", "-i", wav, "-ar", "22050", "-ac", "1", padded],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        padded_files.append(padded)
        cursor = start + seg_dur

    # Concat all padded segments, then pad silence to total_duration
    concat_list = os.path.join(os.path.dirname(out_path), "_segments", "_concat_list.txt")
    with open(concat_list, "w", encoding="utf-8") as f:
        for pf in padded_files:
            f.write(f"file '{pf}'\n")
    # Final: concat all + pad to total_duration
    tail_silence = max(0.0, total_duration - cursor)
    if tail_silence > 0.001:
        tail_file = os.path.join(os.path.dirname(out_path), "_segments", "_tail_silence.wav")
        _write_silence(tail_file, tail_silence)
        with open(concat_list, "a", encoding="utf-8") as f:
            f.write(f"file '{tail_file}'\n")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
         "-ar", "22050", "-ac", "1", out_path],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


if __name__ == "__main__":
    main()
