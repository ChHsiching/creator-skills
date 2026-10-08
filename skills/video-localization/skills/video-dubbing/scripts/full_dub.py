"""Chinese-dub pipeline: IndexTTS2 synthesis → identity-timeline assembly.

The video is NEVER re-timed: every frame keeps its original timestamp and the
dubbed release has exactly the raw video's duration. Each cue's synthesized
audio is placed at its original start; audio that runs past its window (cue
start → next cue's start) is compressed with atempo, but audio shorter than
its window is NEVER stretched — it keeps its natural pace and the window gets
a breathing pause (a 44%-stretch round shipped and was rejected on the spot
as "robotic"; see SKILL.md Step 5). Long cues (>= CHUNK_ON chars) are
synthesized as sentence chunks and concatenated — single takes of very long
text collapse in pace and prosody (the long-line collapse; SKILL.md Step 4).
Subtitles are generated on the original clock, so there is no "dub clock".

Staged design — each stage writes its outputs to disk, so re-runs resume from
cache. Designed to be called by the `cook dub` CLI (thin wrapper that runs this
script as a subprocess), or directly.

Usage (CLI):
  python full_dub.py synth    <output-root> <name>   # stage 1: TTS synthesis
  python full_dub.py assemble <output-root> <name> [--keep-subs]  # stage 2: fit + place + subtitles + burn
  python full_dub.py full     <output-root> <name>   # both, in sequence

Usage (from cook via importlib):
  from full_dub import stage_synth, stage_assemble
  stage_synth(output_root, name)

The retired re-timing path (string-of-pearls timeline + per-segment video
retiming with minterpolate) lives in deprecated/ at the repo root (code snapshot, adjuster, rate report, tests).
It was retired after its output was rejected at ear-check ("plays like
dropped frames": slow segments interpolated at 60fps still visibly hitch);
do not revive it for talking-head content.

Environment:
  INDEXTTS_DIR         — path to the index-tts checkout (default: ~/Git/index-tts)
  DUB_DURATION_FACTOR  — IndexTTS2 duration_factor (default 1.0; ~0.85 is a
                         brisker house pace — see SKILL.md Step 3a)
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
    their cwd — the encode step sets cwd=work for the ass filter's bare
    filename, which would double relative paths."""
    root = Path(output_root).resolve()
    work = root / "dubbed" / "_full"
    return {
        "root": root,
        "raw_mp4": root / "raw" / f"{name}.raw.mp4",
        "en_full_srt": root / "transcript" / f"{name}.en.full.srt",
        "zh_dub_txt": root / "transcript" / "translations_dub.txt",
        "ref_wav": root / "dubbed" / "_reference" / "ref.wav",
        "no_vocals": root / "dubbed" / "no_vocals.wav",
        "work": work,
        "segments": work / "_segments",
        "dub_wav": work / "dub.wav",
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


def _probe_wh(video: Path) -> tuple[int, int]:
    """Probe the video stream's (width, height)."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height",
         "-of", "csv=p=0:s=x", str(video)],
        capture_output=True, text=True,
    )
    w, h = r.stdout.strip().split("x")
    return int(w), int(h)


def _mean_volume(wav: Path) -> float:
    """Mean volume in dB of a wav (for the has-BGM check)."""
    r = subprocess.run(
        ["ffmpeg", "-i", str(wav), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    m = re.search(r"mean_volume:\s*(-?[\d.]+) dB", r.stderr)
    return float(m.group(1)) if m else -99.0


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


def fmt_ts(s):
    ms = int(round(s * 1000))
    h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); sec, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


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


# ---------- assemble math (pure, unit-tested) ----------

def cue_window(cues, i, total_dur):
    """Cue i's absorption window: its start to the next cue's start
    (the last cue runs to the end of the video)."""
    start = cues[i][1]
    nxt = cues[i + 1][1] if i + 1 < len(cues) else total_dur
    return nxt - start


# Long-cue chunking: single takes above this many chars collapse in pace
# (rushed, flat) — synthesized as sentence chunks and concatenated instead.
# Paired with the short-line trap in SKILL.md Step 3a (lines <= 8 syllables
# render at narration pace): the healthy band runs roughly 10-60 chars;
# merge short lines up, chunk long lines down.
CHUNK_ON = 60      # chars above this -> chunked synthesis
CHUNK_MAX = 70     # merge sentence pieces up to this many chars per chunk


def split_chunks(text: str, chunk_max: int = CHUNK_MAX) -> list[str]:
    """Split a long cue at sentence-final punctuation into <= chunk_max-char
    pieces; pieces without punctuation are hard-split at commas. Pure — unit
    tested in tests/test_validation.py."""
    parts = [q for q in re.split(r"(?<=[。？！；])", text) if q.strip()]
    out, cur = [], ""
    for q in parts:
        if len(cur) + len(q) <= chunk_max:
            cur += q
        else:
            if cur:
                out.append(cur)
            cur = q
    if cur:
        out.append(cur)
    final = []
    for q in out:
        while len(q) > chunk_max + 20:  # punctuation-less run: comma hard-split
            cut = q.rfind("，", 0, chunk_max + 20)
            cut = cut if cut > 20 else chunk_max
            final.append(q[:cut + 1])
            q = q[cut + 1:]
        if q:
            final.append(q)
    return final


def _concat_wavs(files, dst):
    """Concatenate wavs (same format) into dst via ffmpeg's concat filter."""
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for f in files:
        cmd += ["-i", str(f)]
    cmd += ["-filter_complex", f"concat=n={len(files)}:v=0:a=1",
            "-c:a", "pcm_s16le", str(dst)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"concat failed: {r.stderr[-200:]}")


def fit_factor(audio_dur, window):
    """atempo factor that lands the audio exactly in the window.
    1.0 means it already fits. ffmpeg atempo accepts 0.5-100 in one filter;
    values outside [0.5, 2.0] mean the text is nowhere near its char budget."""
    if window <= 0:
        return 1.0
    return audio_dur / window


def clamp_factor(factor, lo=0.5, hi=2.0):
    return max(lo, min(hi, factor))


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

    # Two-voice support: optional per-cue speaker map. dubbed/_reference/speakers.txt
    # holds one speaker name per cue; each named speaker needs
    # dubbed/_reference/ref_<speaker>.wav. Without the map, every cue uses the
    # single ref.wav. NOTE: the sent_NNNN.wav cache is keyed by cue index only —
    # after changing speakers.txt or a ref wav, delete the affected segments or
    # the stale voice is reused.
    speakers = None
    refs = {}
    spk_file = p["ref_wav"].parent / "speakers.txt"
    if spk_file.exists():
        labels = [l.strip() for l in spk_file.read_text(encoding="utf-8").splitlines() if l.strip()]
        if len(labels) == len(cues):
            for s in sorted(set(labels)):
                r = p["ref_wav"].parent / f"ref_{s}.wav"
                if not r.exists():
                    log(f"  ERROR: speakers.txt wants ref_{s}.wav but it is missing")
                    sys.exit(1)  # failed: exit non-zero so cook reports ok:false

                refs[s] = r
            speakers = labels
            counts = ", ".join(f"{s}={labels.count(s)}" for s in refs)
            log(f"  two-voice mode: {counts}")
        else:
            log(f"  WARNING: speakers.txt has {len(labels)} lines, expected {len(cues)}; ignoring it")

    done = sum(
        1 for idx, _, _, _, _ in cues
        if (p["segments"] / f"sent_{idx:04d}.wav").exists()
        and (p["segments"] / f"sent_{idx:04d}.wav").stat().st_size > 1000
    )
    log(f"  cached: {done}/{len(cues)}")

    df = float(os.environ.get("DUB_DURATION_FACTOR", "1.0"))

    if done < len(cues):
        log("loading IndexTTS2...")
        t0 = time.time()
        from indextts.infer_v2_5 import IndexTTS2
        tts = IndexTTS2(
            cfg_path=os.path.join(INDEXTTS_DIR, "checkpoints", "config.yaml"),
            model_dir=os.path.join(INDEXTTS_DIR, "checkpoints"),
            use_bf16=False, use_cuda_kernel=False, use_deepspeed=False, device="cpu",
            use_qwen_emo=False,
        )
        log(f"loaded in {time.time()-t0:.1f}s (duration_factor={df})")

    chunk_cache = p["work"] / "_chunkcache"
    chunk_cache.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    n_done = done
    for i, (idx, s, e, en, zh) in enumerate(cues):
        out = p["segments"] / f"sent_{idx:04d}.wav"
        if out.exists() and out.stat().st_size > 1000:
            continue
        t1 = time.time()
        ref = refs[speakers[i]] if speakers else p["ref_wav"]
        if len(zh) > CHUNK_ON:
            # long-line collapse guard: synthesize sentence chunks, concat
            chunks = split_chunks(zh)
            parts = []
            for ci, c in enumerate(chunks):
                cp = chunk_cache / f"c{idx:04d}_{ci:02d}.wav"
                tts.infer(spk_audio_prompt=str(ref), text=c, output_path=str(cp),
                          lang="zh", use_random=False, duration_factor=df)
                parts.append(cp)
            _concat_wavs(parts, out)
        else:
            tts.infer(spk_audio_prompt=str(ref), text=zh, output_path=str(out),
                      lang="zh", use_random=False, duration_factor=df)
        dur = get_dur(out)
        n_done += 1
        elapsed = time.time() - t_start
        rate = (n_done - done) / max(elapsed, 1) if elapsed > 0 else 0
        eta = (len(cues) - n_done) / rate if rate > 0 else 0
        log(f"  [{i+1}/{len(cues)}] idx{idx} {dur:.2f}s zh='{zh[:30]}' elapsed={elapsed/60:.1f}min ETA={eta/60:.1f}min")
    log(f"Stage 1 DONE: {len(cues)} cues synthesized")


# ===== Stage 2: identity-timeline assembly =====

_DUB_BAR_PLAY = 220    # bar height in the ASS coordinate system (PlayRes units)
_BGM_FLOOR_DB = -50.0  # no_vocals mean quieter than this = no real BGM bed
_LOUDNORM_I = -18.0    # dub track loudness; NOT source-matched — a quiet source
                       # master (screencast mics) must not drag the dub down to a whisper


def stage_assemble(output_root, name: str, keep_subs: bool = False):
    p = _paths(output_root, name)
    cues = load_cues(p["en_full_srt"], p["zh_dub_txt"])
    raw_dur = _raw_dur(p["raw_mp4"])
    log(f"Stage 2 (assemble): identity timeline — {len(cues)} cues, video untouched ({raw_dur:.2f}s)")

    if keep_subs:
        for f in (p["dubbing_merged_srt"], p["work"] / "dubbing.en.merged.srt",
                  p["work"] / "dubbing.bilingual.srt"):
            if not f.exists():
                log(f"  ERROR: --keep-subs needs {f} on disk; run a plain assemble first")
                sys.exit(1)

    # 2a. Fit pass — compress-only. Audio longer than its window is atempo'd
    #     down (it would otherwise collide with the next cue); audio SHORTER
    #     keeps its natural pace and 2b pads the tail with silence (a
    #     breathing pause). Time-stretching short audio to fill the window is
    #     forbidden — slowed TTS reads as robotic, and stretching shipped and
    #     was rejected three rounds running before the rule landed.
    log("  2a: fit pass (compress over-window audio only)")
    n_fit = 0
    budget_misses = []
    durs = []
    for i, (idx, s, e, en, zh) in enumerate(cues):
        wav = p["segments"] / f"sent_{idx:04d}.wav"
        if not wav.exists() or wav.stat().st_size <= 1000:
            log(f"  ERROR: missing/truncated {wav.name} — run the synth stage first")
            sys.exit(1)
        d = get_dur(wav)
        window = cue_window(cues, i, raw_dur)
        factor = fit_factor(d, window)
        if factor <= 1.001:  # fits, or shorter: natural pace + pad (no stretch)
            durs.append(d)
            continue
        if factor > 1.5:
            budget_misses.append((idx, factor, d, window))
        k = clamp_factor(factor)
        tmp = wav.with_suffix(".fit.wav")
        r = subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(wav),
             "-af", f"atempo={k:.5f}", "-c:a", "pcm_s16le", str(tmp)],
            capture_output=True, text=True)
        if r.returncode != 0 or not tmp.exists():
            log(f"  ERROR: atempo cue {idx}: {r.stderr[-200:]}")
            sys.exit(1)
        tmp.replace(wav)
        d = get_dur(wav)
        durs.append(d)
        n_fit += 1
    log(f"    fitted {n_fit}/{len(cues)} cues")
    for idx, factor, d, window in budget_misses:
        log(f"    WARNING: idx{idx} factor {factor:.2f} (audio {d:.1f}s vs window {window:.1f}s) — "
            f"char budget miss; edit that sentence and re-synthesize the cue for best quality")

    # 2b. Place audio on the original clock — cue at its original start,
    #     silence to the next start, total exactly raw_dur. Sequential pad
    #     assembly (constant command length; no adelay+amix 32K-argv ceiling).
    log("  2b: place audio on the original clock")
    pad_dir = p["work"] / "_audio_pad"
    if pad_dir.exists():
        shutil.rmtree(pad_dir)
    pad_dir.mkdir(parents=True, exist_ok=True)
    if p["dub_wav"].exists():
        p["dub_wav"].unlink()
    with contextlib.closing(wave.open(str(p["dub_wav"]), "wb")) as out_w:
        out_w.setnchannels(1)
        out_w.setsampwidth(2)
        out_w.setframerate(22050)
        clock = 0.0
        for i, (idx, s, e, en, zh) in enumerate(cues):
            if s > clock + 0.001:
                out_w.writeframes(b"\x00" * (int((s - clock) * 22050) * 2))
                clock = s
            wav = p["segments"] / f"sent_{idx:04d}.wav"
            d = get_dur(wav)
            next_start = cues[i + 1][1] if i + 1 < len(cues) else raw_dur
            pad = max(0.0, next_start - (clock + d))
            padded = pad_dir / ("cue_%04d.wav" % i)
            r = subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-i", str(wav),
                 "-af", "apad=pad_dur=%.3f" % pad,
                 "-ar", "22050", "-ac", "1", "-c:a", "pcm_s16le", str(padded)],
                capture_output=True, text=True)
            if r.returncode != 0:
                log(f"  ERROR: pad cue {idx}: {r.stderr[-300:]}")
                sys.exit(1)
            with contextlib.closing(wave.open(str(padded), "rb")) as w:
                out_w.writeframes(w.readframes(w.getnframes()))
            clock += get_dur(padded)
    if get_dur(p["dub_wav"]) > raw_dur + 0.05:
        tmp = p["work"] / "_dub_full.wav"
        p["dub_wav"].replace(tmp)
        r = subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(tmp),
             "-t", "%.3f" % raw_dur, "-ar", "22050", "-ac", "1",
             "-c:a", "pcm_s16le", str(p["dub_wav"])],
            capture_output=True, text=True)
        tmp.unlink(missing_ok=True)
        if r.returncode != 0:
            log(f"  ERROR: clamp dub.wav: {r.stderr[-300:]}")
            sys.exit(1)
    dub_dur = get_dur(p["dub_wav"])
    if abs(dub_dur - raw_dur) > 0.05:
        log(f"  ERROR: dub.wav {dub_dur:.3f}s != raw {raw_dur:.3f}s — assembly is broken, not shipping")
        sys.exit(1)
    log(f"    dub.wav: {dub_dur:.3f}s (matches raw)")

    # 2c. Subtitles on the ORIGINAL clock (there is no dub clock). ZH window
    #     spans the audio (not just the cue): end = max(cue end, start+audio).
    #     --keep-subs skips this regeneration and reuses the on-disk subtitle
    #     files (the recovery path after a post-burn quality-gate hand edit —
    #     regenerating would wipe it; the ASS is still rebuilt from the
    #     on-disk bilingual SRT).
    subs_mod = _import_subtitles_module()
    if keep_subs:
        log("  2c: --keep-subs — reusing on-disk subtitle files")
        merged_srt = p["dubbing_merged_srt"]
        en_merged_srt = p["work"] / "dubbing.en.merged.srt"
        bilingual_srt = p["work"] / "dubbing.bilingual.srt"
    else:
        log("  2c: generate dubbing.srt + dubbing.en.srt on the original clock")
        zh_lines, en_lines = [], []
        for i, (idx, s, e, en, zh) in enumerate(cues):
            ne = max(e, s + get_dur(p["segments"] / f"sent_{idx:04d}.wav"))
            zh_lines += [str(i + 1), f"{fmt_ts(s)} --> {fmt_ts(ne)}", zh, ""]
            en_lines += [str(i + 1), f"{fmt_ts(s)} --> {fmt_ts(ne)}", en, ""]
        (p["dubbing_srt"]).write_text("\n".join(zh_lines), encoding="utf-8")
        (p["dubbing_en_srt"]).write_text("\n".join(en_lines), encoding="utf-8")

        # Same pipeline the bilingual release runs, on the original clock:
        # shorten splits long cues into single-line cues; EN full sentences
        # get the same treatment so union events fit the bar; biliteral unions
        # them (text repeating across the other language's breakpoints is the
        # union's design, not a defect).
        short_srt = p["work"] / "dubbing.short.srt"
        merged_srt = p["dubbing_merged_srt"]
        _run_subs(subs_mod, ["shorten", str(p["dubbing_srt"]), str(short_srt),
                             "--lang", "zh", "--max-zh", "56"])
        _run_subs(subs_mod, ["merge-short", str(short_srt), str(merged_srt),
                             "--min-dur", "1.2", "--max-len", "56", "--lang", "zh"])
        en_short_srt = p["work"] / "dubbing.en.short.srt"
        en_merged_srt = p["work"] / "dubbing.en.merged.srt"
        _run_subs(subs_mod, ["shorten", str(p["dubbing_en_srt"]), str(en_short_srt),
                             "--lang", "en"])
        _run_subs(subs_mod, ["merge-short", str(en_short_srt), str(en_merged_srt),
                             "--min-dur", "1.2", "--max-len", "160", "--lang", "en"])
        bilingual_srt = p["work"] / "dubbing.bilingual.srt"
        _run_subs(subs_mod, ["biliteral", str(en_merged_srt), str(merged_srt), str(bilingual_srt)])

    # 2d. ASS with correct geometry for THIS frame size. The subtitles module's
    #     coordinate system is 1920 x (1080 + bar); libass scales it to the
    #     real frame per-axis. For the bar to start exactly at the video's
    #     bottom edge on a frame that is not 1920x1080 16:9, the y-scale must
    #     be exactly H/1080, so: real pad = bar_play * H/1080, and
    #     PlayResX = W * 1080 / H (uniform scale, no glyph stretch).
    W, H = _probe_wh(p["raw_mp4"])
    play_x = round(W * 1080 / H)
    pad_px = round(_DUB_BAR_PLAY * H / 1080)
    if play_x != 1920:
        log(f"  2d: non-1080p frame {W}x{H} — PlayResX={play_x}, real bar={pad_px}px "
            f"(bar stays {_DUB_BAR_PLAY} in coordinate units)")
    subs_mod.PLAY_RES_X = play_x
    cooked_ass = p["work"] / "dubbing.cooked.ass"
    _run_subs(subs_mod, ["ass", str(bilingual_srt), str(cooked_ass),
                         "--bottom-bar", str(_DUB_BAR_PLAY)])
    shutil.copyfile(cooked_ass, p["burn_ass"])

    log("  2e: copy upload subtitles to cloud-srt/")
    p["cloud_srt"].parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(merged_srt, p["cloud_srt"])
    shutil.copyfile(en_merged_srt, p["cloud_srt_en"])

    # 2f. Encode — raw video stream untouched (identity), pad the bar, burn the
    #     ASS, mix the dub (+ no_vocals bed only when the source really has
    #     BGM), loudnorm to house level. Run from the work dir so the ass
    #     filter gets a bare filename (Windows rejects C: paths in ass=).
    log(f"  2f: encode (pad +{pad_px}px bar, identity video)")
    bgm_bed = (p["no_vocals"].exists()
               and _mean_volume(p["no_vocals"]) > _BGM_FLOOR_DB)
    if bgm_bed:
        log("    BGM detected in no_vocals — mixing bed at -18dB")
        a_filter = ("[2:a]volume=-18dB[nv];[1:a][nv]amix=inputs=2:duration=first:normalize=0"
                    f",loudnorm=I={_LOUDNORM_I}:TP=-1.5:LRA=11[a]")
        cmd = ["ffmpeg", "-y", "-i", str(p["raw_mp4"]), "-i", str(p["dub_wav"]),
               "-i", str(p["no_vocals"]),
               "-vf", f"pad=iw:ih+{pad_px}:0:0:color=black,ass=burn.ass",
               "-filter_complex", a_filter, "-map", "0:v", "-map", "[a]"]
    else:
        a_filter = f"loudnorm=I={_LOUDNORM_I}:TP=-1.5:LRA=11"
        cmd = ["ffmpeg", "-y", "-i", str(p["raw_mp4"]), "-i", str(p["dub_wav"]),
               "-vf", f"pad=iw:ih+{pad_px}:0:0:color=black,ass=burn.ass",
               "-af", a_filter, "-map", "0:v", "-map", "1:a"]
    cmd += ["-c:v", "libx264", "-preset", "faster", "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
            "-shortest", str(p["final_mp4"])]
    p["final_mp4"].parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(cmd, cwd=str(p["work"]), capture_output=True, text=True)
    if r.returncode != 0:
        log(f"  ERROR: final encode: {r.stderr[-500:]}")
        log("Stage 2 FAILED")
        sys.exit(1)  # failed: exit non-zero so cook reports ok:false

    final_dur = probe_dur(p["final_mp4"])
    if abs(final_dur - raw_dur) > 0.5:
        log(f"  ERROR: final {final_dur:.2f}s != raw {raw_dur:.2f}s — identity violated")
        sys.exit(1)
    log(f"    DONE: {p['final_mp4']} ({final_dur:.2f}s, matches raw)")
    log("Stage 2 DONE")


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
    "assemble": stage_assemble,
}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    output_root = sys.argv[2]
    name = sys.argv[3] if len(sys.argv) > 3 else None
    flags = [a for a in sys.argv[4:] if a.startswith("--")]
    keep_subs = "--keep-subs" in flags
    if keep_subs and cmd != "assemble":
        print("--keep-subs applies to the assemble stage only")
        sys.exit(1)
    if cmd == "full":
        stage_synth(output_root, name)
        stage_assemble(output_root, name)
        log("all stages complete")
    elif cmd in _STAGES:
        if cmd == "assemble":
            stage_assemble(output_root, name, keep_subs=keep_subs)
        else:
            _STAGES[cmd](output_root, name)
    else:
        print(f"unknown stage: {cmd}\n{__doc__}")
        sys.exit(1)
