"""Full Chinese-dub pipeline: IndexTTS2 synthesis → string-of-pearls timeline →
bi-directional video re-timing (with minterpolate) → concat + audio + burn.

Staged design — each stage writes its outputs to disk, so re-runs resume from
cache. Designed to be called by the `cook dub` CLI (thin wrapper that imports
this module), or directly via CLI.

Usage (CLI):
  python full_dub.py synth    <output-root> <name>   # stage 1: TTS synthesis
  python full_dub.py timeline <output-root> <name>   # stage 2: timeline math
  python full_dub.py retime   <output-root> <name>   # stage 3: video segments + interpolation
  python full_dub.py burn     <output-root> <name>   # stage 4: concat + audio + subtitles + burn
  python full_dub.py full     <output-root> <name>   # all four, in sequence

Usage (from cook via importlib):
  from full_dub import stage_synth, stage_timeline, stage_retime, stage_burn
  stage_synth(output_root, name)

Environment:
  INDEXTTS_DIR  — path to the index-tts checkout (default: ~/Git/index-tts)
"""
import os, sys, time, re, json, subprocess, contextlib, wave, shutil
from pathlib import Path

# ===== single-thread MUST be set before any numerical import (坑 5) =====
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

# IndexTTS2 checkout location — env-overridable for non-default installs
INDEXTTS_DIR = os.environ.get("INDEXTTS_DIR", str(Path.home() / "Git" / "index-tts"))


# ---------- path derivation ----------

def _paths(output_root: str | Path, name: str) -> dict:
    """Derive every path this pipeline needs from (output_root, name).

    Root is resolved to absolute so downstream ffmpeg calls work regardless of
    their cwd — Stage 4f sets cwd=work for the ass filter's bare filename, which
    would double relative paths (e.g. dubbed/_full/ + dubbed/_full/video_adjusted.mp4)."""
    root = Path(output_root).resolve()
    work = root / "dubbed" / "_full"
    return {
        "root": root,
        "raw_mp4": root / "raw" / f"{name}.raw.mp4",
        "en_full_srt": root / "transcript" / f"{name}.en.full.srt",
        "zh_dub_txt": root / "transcript" / "translations_dub.txt",
        "ref_wav": root / "dubbed" / "_reference" / "ref.wav",
        "work": work,
        "segments": work / "_segments",
        "vsegs": work / "_vsegs",
        "timeline_json": work / "timeline.json",
        "dub_wav": work / "dub.wav",
        "video_adjusted": work / "video_adjusted.mp4",
        "dubbing_srt": work / "dubbing.srt",
        "dubbing_en_srt": work / "dubbing.en.srt",
        "dubbing_merged_srt": work / "dubbing.merged.srt",
        "burn_ass": work / "burn.ass",
        "final_mp4": root / "cooked" / f"{name}.dubbed.mp4",
        "cloud_srt": root / "cloud-srt" / "zh.dub.srt",
        "cloud_srt_en": root / "cloud-srt" / "en.dub.srt",
    }


def _raw_dur(raw_mp4: Path) -> float:
    """Probe the raw video's duration."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(raw_mp4)],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip())


# ---------- small utilities ----------

def get_dur(p):
    with contextlib.closing(wave.open(str(p), "rb")) as w:
        return w.getnframes() / float(w.getframerate())


def probe_dur(p):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(p)],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip())


# ---------- validation helpers (ticket #3) ----------
#
# These are pure functions that accept an injectable `prober` so they can be
# unit-tested without ffmpeg or real media files. stage_retime/stage_burn pass
# the real probe_dur at the call site; tests pass a lambda.

def _vseg_is_valid(out: Path, expected_dur: float, prober=None) -> tuple[bool, str]:
    """Check a generated video segment is readable and has positive duration.

    Returns (True, "") when valid, (False, reason) otherwise. The corruption
    symptom this exists to catch: ffmpeg writes a truncated file with no moov
    atom, ffprobe then returns 0.0 or raises — that segment must be redone or
    the concat will silently drop it and truncate the final video.
    """
    prober = prober or probe_dur
    if not out.exists():
        return False, f"missing {out.name}"
    if out.stat().st_size < 1000:
        return False, f"{out.name} truncated ({out.stat().st_size} bytes)"
    try:
        dur = prober(out)
    except Exception as e:
        return False, f"{out.name} probe raised: {e}"
    if dur <= 0:
        return False, f"{out.name} probe returned 0 (moov atom missing?)"
    return True, ""


def _verify_all_vsegs(vsegs_dir: Path, timeline: list, prober=None) -> list[int]:
    """Return the list of segment indices whose vseg is missing or unreadable.

    Used by stage_retime after the generation loop to confirm every expected
    v_{i:04d}.mp4 came out clean. Empty list = all good.
    """
    bad = []
    for i, seg in enumerate(timeline):
        out = vsegs_dir / f"v_{i:04d}.mp4"
        ok, _ = _vseg_is_valid(out, seg.get("new_dur", 0.0), prober=prober)
        if not ok:
            bad.append(i)
    return bad


def _concat_duration_ok(probed: float, expected: float, tol: float = 0.05) -> tuple[bool, str]:
    """Check the concatenated video's duration matches the timeline total.

    Returns (True, "") within tolerance, (False, reason) otherwise. The
    silent-truncation failure mode: concat demuxer skips corrupted vsegs, so
    the result is shorter than the timeline's sum of new_durs. We abort if the
    difference exceeds `tol` (default 5%, measured against the timeline total).
    """
    if expected <= 0:
        return False, f"expected duration {expected} <= 0 (timeline empty?)"
    if probed <= 0:
        return False, f"probed duration {probed} <= 0 (concat failed to probe?)"
    diff = probed - expected
    rel = abs(diff) / expected
    if rel > tol:
        direction = "short" if diff < 0 else "long"
        return False, (
            f"concat duration {probed:.2f}s is {rel*100:.1f}% {direction} of "
            f"timeline total {expected:.2f}s (tolerance {tol*100:.0f}%)"
        )
    return True, ""


def fmt_ts(s):
    ms = int(round(s * 1000))
    h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); sec, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def fmt_ass_ts(s):
    ms = int(round(s * 1000))
    h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); sec, ms = divmod(ms, 1000)
    return f"{h:d}:{m:02d}:{sec:02d}.{ms//10:02d}"


def _ts(s):
    s = s.replace(",", ".")
    h, m, sec = s.split(":")
    return int(h) * 3600 + int(m) * 60 + float(sec)


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------- cue loading ----------

_CUE_RE = re.compile(
    r"(\d+)\s*\n(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*\n"
    r"(.*?)(?=\n\n|\n\d+\s*\n|\Z)", re.DOTALL,
)


def load_cues(en_full_srt: Path, zh_dub_txt: Path):
    """Parse en.full.srt + translations_dub.txt into a list of (idx, start, end, en, zh)."""
    cues = []
    with open(en_full_srt, encoding="utf-8") as f:
        for m in _CUE_RE.finditer(f.read()):
            cues.append((int(m[1]), _ts(m[2]), _ts(m[3]), re.sub(r"\s+", " ", m[4].strip())))
    with open(zh_dub_txt, encoding="utf-8") as f:
        zh = [l.rstrip("\n") for l in f if l.strip()]
    assert len(cues) == len(zh), f"line count mismatch: en={len(cues)} zh={len(zh)}"
    return [(idx, s, e, en, z) for (idx, s, e, en), z in zip(cues, zh)]


# ===== Stage 1: TTS synthesis =====

def stage_synth(output_root, name: str):
    p = _paths(output_root, name)
    p["segments"].mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, INDEXTTS_DIR)
    for mod in list(sys.modules):
        if mod.startswith("indextts"):
            del sys.modules[mod]
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)

    cues = load_cues(p["en_full_srt"], p["zh_dub_txt"])
    log(f"Stage 1 (synth): {len(cues)} cues (single-threaded IndexTTS2)")

    done = sum(
        1 for idx, _, _, _, _ in cues
        if (p["segments"] / f"sent_{idx:04d}.wav").exists()
        and (p["segments"] / f"sent_{idx:04d}.wav").stat().st_size > 1000
    )
    log(f"  cached: {done}/{len(cues)}")

    if done < len(cues):
        log("loading IndexTTS2...")
        t0 = time.time()
        from indextts.infer_v2 import IndexTTS2
        tts = IndexTTS2(
            cfg_path=os.path.join(INDEXTTS_DIR, "checkpoints", "config.yaml"),
            model_dir=os.path.join(INDEXTTS_DIR, "checkpoints"),
            use_fp16=False, use_cuda_kernel=False, use_deepspeed=False, device="cpu",
        )
        log(f"loaded in {time.time()-t0:.1f}s")

    t_start = time.time()
    n_done = done
    for i, (idx, s, e, en, zh) in enumerate(cues):
        out = p["segments"] / f"sent_{idx:04d}.wav"
        if out.exists() and out.stat().st_size > 1000:
            continue
        t1 = time.time()
        tts.infer(spk_audio_prompt=str(p["ref_wav"]), text=zh, output_path=str(out), use_random=False)
        dur = get_dur(out)
        n_done += 1
        elapsed = time.time() - t_start
        rate = (n_done - done) / max(elapsed, 1) if elapsed > 0 else 0
        eta = (len(cues) - n_done) / rate if rate > 0 else 0
        log(f"  [{i+1}/{len(cues)}] idx{idx} {dur:.2f}s zh='{zh[:30]}' elapsed={elapsed/60:.1f}min ETA={eta/60:.1f}min")
    log(f"Stage 1 DONE: {len(cues)} cues synthesized")


# ===== Stage 2: timeline (string-of-pearls) =====

def stage_timeline(output_root, name: str):
    p = _paths(output_root, name)
    p["work"].mkdir(parents=True, exist_ok=True)
    raw_dur = _raw_dur(p["raw_mp4"])

    cues = load_cues(p["en_full_srt"], p["zh_dub_txt"])
    log(f"Stage 2 (timeline): string-of-pearls construction")

    zh_durs = []
    for idx, s, e, en, zh in cues:
        seg = p["segments"] / f"sent_{idx:04d}.wav"
        if not seg.exists():
            log(f"  ERROR: missing {seg}, run synth first"); return
        zh_durs.append(get_dur(seg))

    timeline = []
    prev_end = 0.0
    for i, (idx, s, e, en, zh) in enumerate(cues):
        if s > prev_end:
            timeline.append({"kind": "gap", "orig_start": prev_end, "orig_end": s, "idx": None})
        timeline.append({"kind": "cue", "orig_start": s, "orig_end": e, "idx": idx,
                         "zh_dur": zh_durs[i], "text": zh, "en": en})
        prev_end = e
    if prev_end < raw_dur:
        timeline.append({"kind": "gap", "orig_start": prev_end, "orig_end": raw_dur, "idx": None})

    new_t = 0.0
    for seg in timeline:
        orig_dur = seg["orig_end"] - seg["orig_start"]
        new_dur = seg["zh_dur"] if seg["kind"] == "cue" else orig_dur
        seg["new_start"] = new_t
        seg["new_end"] = new_t + new_dur
        seg["new_dur"] = new_dur
        seg["speed"] = orig_dur / new_dur if new_dur > 0 else 1.0
        new_t += new_dur

    total_new = new_t
    cues_seg = [s for s in timeline if s["kind"] == "cue"]
    fast = [s for s in cues_seg if s["speed"] > 1.05]
    slow = [s for s in cues_seg if s["speed"] < 0.95]
    log(f"  new total: {total_new:.2f}s (raw {raw_dur:.2f}s, {'shorter' if total_new<raw_dur else 'longer'} by {abs(total_new-raw_dur):.1f}s)")
    log(f"  speed-up cues: {len(fast)}, slow-down cues: {len(slow)}")

    with open(p["timeline_json"], "w", encoding="utf-8") as f:
        json.dump({"timeline": timeline, "total_new": total_new, "raw_dur": raw_dur}, f, ensure_ascii=False, indent=2)
    log(f"Stage 2 DONE: {p['timeline_json']}")


# ===== Stage 3: video segments + minterpolate =====

def stage_retime(output_root, name: str):
    p = _paths(output_root, name)
    p["vsegs"].mkdir(parents=True, exist_ok=True)
    if not p["timeline_json"].exists():
        log("  ERROR: missing timeline.json, run timeline first"); return

    with open(p["timeline_json"], encoding="utf-8") as f:
        data = json.load(f)
    timeline = data["timeline"]
    log(f"Stage 3 (retime): {len(timeline)} segments")

    slow_segs = [s for s in timeline if s["kind"] == "cue" and s["speed"] < 0.95]
    slow_video_dur = sum(s["new_dur"] for s in slow_segs)
    log(f"  interpolation segments: {len(slow_segs)}, ~{slow_video_dur*23/60:.0f}min estimated")

    t_stage = time.time()
    MAX_SEG_RETRIES = 2  # redo a corrupted segment this many times before giving up
    for i, seg in enumerate(timeline):
        out = p["vsegs"] / f"v_{i:04d}.mp4"
        if out.exists() and out.stat().st_size > 1000:
            # Resume from cache — but still validate; a previous run may have
            # left a truncated file (moov atom missing) that ffprobe rejects.
            ok, reason = _vseg_is_valid(out, seg.get("new_dur", 0.0))
            if ok:
                continue
            log(f"  [{i+1}/{len(timeline)}] cached {out.name} invalid ({reason}) — regenerating")
            try:
                out.unlink()
            except OSError:
                pass

        os_v = seg["orig_start"]; oe_v = seg["orig_end"]
        orig_dur = oe_v - os_v
        new_dur = seg["new_dur"]
        factor = new_dur / orig_dur if orig_dur > 0 else 1.0
        speed = seg["speed"]

        if seg["kind"] == "cue" and speed < 0.95:
            vf = (f"setpts={factor:.6f}*PTS,"
                  f"minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:"
                  f"me_mode=bidir:me=epzs:vsbmc=1")
            label = f"slow {speed:.2f}x+interp"
        elif seg["kind"] == "cue":
            vf = f"setpts={factor:.6f}*PTS"
            label = f"{'fast' if speed>1.05 else 'keep'} {speed:.2f}x"
        else:
            vf = "null"
            label = "gap"

        cmd = ["ffmpeg", "-y", "-ss", f"{os_v:.3f}", "-t", f"{orig_dur:.3f}",
               "-i", str(p["raw_mp4"]),
               "-vf", vf, "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
               "-r", "60", str(out)]

        # Retry loop: ffmpeg can return 0 yet write a truncated file (moov atom
        # missing) that ffprobe rejects. Probe each output; redo on failure.
        for attempt in range(MAX_SEG_RETRIES + 1):
            t0 = time.time()
            r = subprocess.run(cmd, capture_output=True, text=True)
            wall = time.time() - t0
            if r.returncode != 0:
                log(f"  [{i+1}/{len(timeline)}] ERR seg {i} (attempt {attempt+1}): {r.stderr[-200:]}")
                ok, reason = False, "ffmpeg non-zero exit"
            else:
                ok, reason = _vseg_is_valid(out, new_dur)
            if ok:
                break
            # Corrupted output — delete so the retry (or a later run) regenerates.
            try:
                out.unlink()
            except OSError:
                pass
            if attempt < MAX_SEG_RETRIES:
                log(f"  [{i+1}/{len(timeline)}] seg {i} invalid ({reason}) — retry {attempt+1}/{MAX_SEG_RETRIES}")

        if ok:
            elapsed = time.time() - t_stage
            n_done = i + 1
            rate = n_done / max(elapsed, 1)
            eta = (len(timeline) - n_done) / rate if rate > 0 else 0
            log(f"  [{n_done}/{len(timeline)}] {label} {orig_dur:.1f}s→{new_dur:.1f}s wall={wall:.0f}s ETA={eta/60:.0f}min")
        else:
            log(f"  [{i+1}/{len(timeline)}] FAILED seg {i} after {MAX_SEG_RETRIES+1} attempts: {reason}")

    # Post-loop: confirm every expected vseg exists and is readable. A missing
    # vseg here would silently truncate the concat, so name the bad ones and
    # abort instead of producing a short final video.
    bad = _verify_all_vsegs(p["vsegs"], timeline)
    if bad:
        log(f"  ERROR: {len(bad)} segment(s) missing or unreadable: {bad}")
        log(f"  Stage 3 ABORTED — re-run `retime` to regenerate, or investigate ffmpeg/minterpolate failures on those segments.")
        return
    log(f"Stage 3 DONE — {len(timeline)} segments verified")


# ===== Stage 4: concat + audio + subtitles + burn =====

# The dub burns bilingual subtitles in the same bottom-bar layout as the
# bilingual release from video-subtitle: EN (full sentences mapped onto the
# dub's re-timed clock) over ZH (shorten/merge-short fragments). Font sizes
# and margins are subtitles.py's bottom-bar defaults (ZH 64 / EN 44, marginv
# 140) — no overrides here, so the two releases can't drift apart.
_DUB_BAR = 220


def stage_burn(output_root, name: str):
    p = _paths(output_root, name)
    if not p["timeline_json"].exists():
        log("  ERROR: missing timeline.json"); return
    with open(p["timeline_json"], encoding="utf-8") as f:
        data = json.load(f)
    timeline = data["timeline"]
    log(f"Stage 4 (burn): concat + audio + subtitles + burn")

    # 4a: concat video segments
    log("  4a: concat segments")
    concat_txt = p["work"] / "_concat.txt"
    with open(concat_txt, "w") as f:
        for i in range(len(timeline)):
            f.write(f"file '{(p['vsegs'] / f'v_{i:04d}.mp4').as_posix()}'\n")
    r_concat = subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
         "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-r", "60",
         str(p["video_adjusted"])],
        capture_output=True, text=True,
    )
    if r_concat.returncode != 0:
        # Concat failing almost always means an upstream vseg is corrupt (stage
        # 3's validation should have caught this, but a filesystem race or a
        # mid-run kill can leave bad state). Abort here rather than producing a
        # silently-truncated video downstream.
        log(f"    ERR concat failed (rc={r_concat.returncode}): {r_concat.stderr[-400:]}")
        log(f"    Stage 4 ABORTED — re-run `retime` to regenerate vsegs, then retry burn.")
        return

    concat_dur = probe_dur(p["video_adjusted"])
    total_new = data.get("total_new")
    if total_new:
        ok, reason = _concat_duration_ok(concat_dur, total_new)
        if not ok:
            log(f"    ERR {reason}")
            log(f"    Stage 4 ABORTED — concat duration doesn't match timeline; a vseg may be corrupt or dropped. Re-run `retime`.")
            return
    log(f"    video_adjusted.mp4: {concat_dur:.2f}s (timeline total {total_new:.2f}s)" if total_new else f"    video_adjusted.mp4: {concat_dur:.2f}s")

    # 4b: place audio (adelay + amix on silence base)
    log("  4b: place audio (adelay + amix)")
    audio_plan = []
    for seg in timeline:
        if seg["kind"] != "cue":
            continue
        ns, ne = seg["new_start"], seg["new_end"]
        audio_plan.append((p["segments"] / f"sent_{seg['idx']:04d}.wav",
                           int(round(ns * 1000)), ns, ne, seg["text"]))
    target = probe_dur(p["video_adjusted"])
    inputs = ["-f", "lavfi", "-t", f"{target}", "-i", "anullsrc=r=22050:cl=mono"]
    filter_parts = ["[0:a]volume=0[base]"]
    for i, (seg, delay_ms, _, _, _) in enumerate(audio_plan):
        inputs.extend(["-i", str(seg)])
        filter_parts.append(f"[{i+1}:a]adelay={delay_ms}|{delay_ms}[d{i+1}]")
    mix = "[base]" + "".join(f"[d{i+1}]" for i in range(len(audio_plan)))
    filter_str = ";".join(filter_parts) + f";{mix}amix=inputs={len(audio_plan)+1}:duration=first:normalize=0[aout]"
    r = subprocess.run(
        ["ffmpeg", "-y"] + inputs + ["-filter_complex", filter_str, "-map", "[aout]",
         "-t", f"{target}", "-ar", "22050", "-ac", "1", str(p["dub_wav"])],
        capture_output=True, text=True,
    )
    log(f"    dub.wav: {get_dur(p['dub_wav']):.2f}s" + (f" ERR:{r.stderr[-200:]}" if r.returncode else ""))

    for i in range(1, len(audio_plan)):
        assert audio_plan[i][2] >= audio_plan[i-1][3], f"overlap! cue{i} {audio_plan[i][2]} < {audio_plan[i-1][3]}"
    log(f"    ✓ {len(audio_plan)} cues, no overlap")

    # 4c: generate SRTs (pre-shorten, on the new timeline)
    log("  4c: generate dubbing.srt + dubbing.en.srt")
    srt_lines = []
    for i, (_, _, cs, ce, text) in enumerate(audio_plan):
        srt_lines += [str(i+1), f"{fmt_ts(cs)} --> {fmt_ts(ce)}", text, ""]
    with open(p["dubbing_srt"], "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))

    # EN side: full-sentence English (en.full.srt texts) placed on the
    # re-timed clock. Cue idx i's window [new_start, new_end] is exactly where
    # its Chinese audio plays, so the mapping is index-aligned by construction.
    # This SRT feeds the biliteral merge in 4d and ships as cloud-srt/en.dub.srt.
    en_texts = {}
    with open(p["en_full_srt"], encoding="utf-8") as f:
        for m in _CUE_RE.finditer(f.read()):
            en_texts[int(m[1])] = re.sub(r"\s+", " ", m[4].strip())
    n_cues = sum(1 for s in timeline if s["kind"] == "cue")
    assert len(en_texts) == n_cues, \
        f"en.full.srt has {len(en_texts)} cues but timeline has {n_cues} — regenerate timeline"
    en_srt_lines = []
    for seg in timeline:
        if seg["kind"] != "cue":
            continue
        en_srt_lines += [str(seg["idx"]),
                         f"{fmt_ts(seg['new_start'])} --> {fmt_ts(seg['new_end'])}",
                         en_texts[seg["idx"]], ""]
    with open(p["dubbing_en_srt"], "w", encoding="utf-8") as f:
        f.write("\n".join(en_srt_lines))

    # 4d: shorten + merge-short + biliteral + ass (same pipeline as video-subtitle)
    # shorten splits long cues into single-line cues, allocating sub-cue time
    # by display-width proportion (wlen). This keeps each cue one zh line.
    log("  4d: shorten + merge-short + biliteral + ass (via video-subtitle's subtitles.py)")
    subs_mod = _import_subtitles_module()
    short_srt = p["work"] / "dubbing.short.srt"
    merged_srt = p["dubbing_merged_srt"]
    bilingual_srt = p["work"] / "dubbing.bilingual.srt"
    cooked_ass = p["work"] / "dubbing.cooked.ass"
    _run_subs(subs_mod, ["shorten", str(p["dubbing_srt"]), str(short_srt),
                         "--lang", "zh", "--max-zh", "56"])
    _run_subs(subs_mod, ["merge-short", str(short_srt), str(merged_srt),
                         "--min-dur", "1.2", "--max-len", "56", "--lang", "zh"])
    # biliteral unions the full-sentence EN with the fragmented ZH. EN spans
    # whole sentences while ZH breaks inside them, so EN repeats across the
    # ZH fragments — the bilingual release's structural repetition with the
    # languages' roles swapped. Flag with care in Gate C: EN repeating across
    # consecutive cues is the design, not a defect.
    _run_subs(subs_mod, ["biliteral", str(p["dubbing_en_srt"]),
                         str(merged_srt), str(bilingual_srt)])
    _run_subs(subs_mod, ["ass", str(bilingual_srt), str(cooked_ass),
                         "--bottom-bar", str(_DUB_BAR)])
    shutil.copyfile(cooked_ass, p["burn_ass"])

    # 4e: copy upload subtitles to cloud-srt/
    log("  4e: copy upload subtitles to cloud-srt/")
    p["cloud_srt"].parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(merged_srt, p["cloud_srt"])
    shutil.copyfile(p["dubbing_en_srt"], p["cloud_srt_en"])

    # 4f: burn (run from work dir so ASS uses relative path — Windows ass filter rejects C: paths)
    log(f"  4f: burn (pad + ass, bottom-bar {_DUB_BAR})")
    p["final_mp4"].parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", str(p["video_adjusted"]), "-i", str(p["dub_wav"]),
         "-vf", f"pad=iw:ih+{_DUB_BAR}:0:0:color=black,ass=burn.ass",
         "-map", "0:v", "-map", "1:a",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", "60",
         "-c:a", "aac", "-b:a", "128k", "-shortest", str(p["final_mp4"])],
        cwd=str(p["work"]), capture_output=True, text=True,
    )
    if r.returncode != 0:
        log(f"    ERR: {r.stderr[-500:]}")
    else:
        log(f"    DONE: {p['final_mp4']} ({probe_dur(p['final_mp4']):.2f}s)")
    log(f"Stage 4 DONE")


# ---------- video-subtitle module loader (mirrors cook's pattern) ----------

def _import_subtitles_module():
    """Load video-subtitle's subtitles.py via importlib, same as cook does."""
    candidates = [
        Path.home() / ".agents" / "skills" / "video-subtitle" / "scripts" / "subtitles.py",
        Path.home() / ".zcode" / "skills" / "video-subtitle" / "scripts" / "subtitles.py",
        Path.home() / ".claude" / "skills" / "video-subtitle" / "scripts" / "subtitles.py",
    ]
    for cand in candidates:
        if cand.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("subtitles", cand)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise FileNotFoundError("subtitles.py not found — install video-subtitle skill")


def _run_subs(mod, argv):
    old = sys.argv
    sys.argv = ["subtitles.py"] + argv
    try:
        mod.main()
    finally:
        sys.argv = old


# ---------- CLI entry ----------

_STAGES = {
    "synth": stage_synth,
    "timeline": stage_timeline,
    "retime": stage_retime,
    "burn": stage_burn,
}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    output_root = sys.argv[2]
    name = sys.argv[3] if len(sys.argv) > 3 else None
    if cmd == "full":
        stage_synth(output_root, name)
        stage_timeline(output_root, name)
        stage_retime(output_root, name)
        stage_burn(output_root, name)
        log("all stages complete")
    elif cmd in _STAGES:
        _STAGES[cmd](output_root, name)
    else:
        print(f"unknown stage: {cmd}\n{__doc__}")
        sys.exit(1)
