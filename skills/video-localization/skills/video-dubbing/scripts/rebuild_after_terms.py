"""术语修正后的增量重建：stage2(全) + stage3(仅7条) + stage4(全)。
复用 full_dub.py 的函数，但 stage3 只重做变化的段。
"""
import os, sys, json, subprocess, shutil, time, contextlib, wave

# 复用 full_dub.py 的所有函数和常量
sys.path.insert(0, r"C:\Users\Administrator\Git\video-subtitle\matt-pocock\dont-waste-time-on-specs-prototype-instead\dubbed\_test_indextts")
import full_dub

# 改动的 cue idx（TTS 时长变了，对应视频段要重做）
CHANGED_CUES = {50, 53, 54, 55, 56, 61, 74}

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

# ===== Stage 2: 重算时间轴（全量）=====
log("Stage 2: 重算时间轴")
full_dub.stage2()

# ===== Stage 3: 增量重插帧（只重做 CHANGED_CUES 对应的段）=====
with open(full_dub.TIMELINE_JSON, encoding="utf-8") as f:
    data = json.load(f)
timeline = data["timeline"]
log(f"Stage 3: 增量重做 {len(CHANGED_CUES)} 条变化的 cue 段")

n_redone = 0
t_stage = time.time()
for i, seg in enumerate(timeline):
    if seg["kind"] != "cue" or seg["idx"] not in CHANGED_CUES:
        continue
    out = os.path.join(full_dub.VSEG_DIR, f"v_{i:04d}.mp4")
    # 删旧段，触发重做
    if os.path.exists(out):
        os.remove(out)

    os_v = seg["orig_start"]; oe_v = seg["orig_end"]
    orig_dur = oe_v - os_v
    new_dur = seg["new_dur"]
    factor = new_dur / orig_dur if orig_dur > 0 else 1.0
    speed = seg["speed"]

    if speed < 0.95:
        vf = (f"setpts={factor:.6f}*PTS,"
              f"minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:"
              f"me_mode=bidir:me=epzs:vsbmc=1")
        label = f"放慢{speed:.2f}x+插帧"
    elif speed > 1.05:
        vf = f"setpts={factor:.6f}*PTS"
        label = f"快进{speed:.2f}x"
    else:
        vf = f"setpts={factor:.6f}*PTS"
        label = f"不变{speed:.2f}x"

    t0 = time.time()
    cmd = ["ffmpeg","-y","-ss",f"{os_v:.3f}","-t",f"{orig_dur:.3f}","-i",full_dub.RAW_MP4,
           "-vf",vf,"-an","-c:v","libx264","-preset","ultrafast","-crf","18",
           "-r","60",out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    wall = time.time() - t0
    if r.returncode != 0:
        log(f"  ERR seg {i} (idx{seg['idx']}): {r.stderr[-200:]}")
    else:
        log(f"  [{n_redone+1}/{len(CHANGED_CUES)}] idx{seg['idx']} {label} {orig_dur:.1f}s→{new_dur:.1f}s wall={wall:.0f}s")
    n_redone += 1
log(f"Stage 3 DONE: 重做 {n_redone} 段，{(time.time()-t_stage)/60:.1f}min")

# ===== Stage 4: concat + 音频 + 字幕(shorten+ass) + 烧录 =====
log("Stage 4: concat + 音频 + 字幕 + 烧录")
full_dub.stage4()

# ===== 额外：生成 shorten 版字幕 + 烧录 v2（字幕不超宽版）=====
log("Stage 4b: shorten 字幕 + 烧录 cooked 参数版")
SCRIPTS = r"C:\Users\Administrator\.agents\skills\video-subtitle\scripts"
DUB_SRT = full_dub.WORK_DIR + r"\dubbing.srt"
SHORT_SRT = full_dub.WORK_DIR + r"\dubbing.short.srt"
MERGED_SRT = full_dub.WORK_DIR + r"\dubbing.merged.srt"
ZH_ASS = full_dub.WORK_DIR + r"\dubbing.zh.ass"

subprocess.run(["python", SCRIPTS + r"\subtitles.py", "shorten",
                DUB_SRT, SHORT_SRT, "--lang", "zh", "--max-zh", "42"],
               capture_output=True, text=True)
subprocess.run(["python", SCRIPTS + r"\subtitles.py", "merge-short",
                SHORT_SRT, MERGED_SRT, "--min-dur", "1.2", "--max-len", "42"],
               capture_output=True, text=True)
subprocess.run(["python", SCRIPTS + r"\subtitles.py", "ass",
                MERGED_SRT, full_dub.WORK_DIR + r"\dubbing.cooked.ass", "--bottom-bar", "180"],
               capture_output=True, text=True)
# 去空 EN 行
with open(full_dub.WORK_DIR + r"\dubbing.cooked.ass", encoding="utf-8") as f:
    lines = [l for l in f if not (l.startswith("Dialogue:") and ",EN,,0,0,0,," in l)]
with open(ZH_ASS, "w", encoding="utf-8") as f:
    f.write("".join(lines))

# 烧录 v2（字号64 黑条180）
shutil.copy(ZH_ASS, full_dub.WORK_DIR + r"\burn_zh.ass")
final_v2 = full_dub.OUT + r"\cooked\dont-waste-time-on-specs-prototype-instead.dubbed.v2.mp4"
r = subprocess.run(["ffmpeg","-y","-i",full_dub.WORK_DIR + r"\video_adjusted.mp4",
                    "-i",full_dub.WORK_DIR + r"\dub.wav",
                    "-vf","pad=iw:ih+180:0:0:color=black,ass=burn_zh.ass",
                    "-map","0:v","-map","1:a",
                    "-c:v","libx264","-preset","medium","-crf","20","-r","60",
                    "-c:a","aac","-b:a","128k","-shortest",final_v2],
                   cwd=full_dub.WORK_DIR, capture_output=True, text=True)
if r.returncode != 0:
    log(f"  v2 ERR: {r.stderr[-300:]}")
else:
    dur = full_dub.probe_dur(final_v2)
    log(f"  v2 DONE: {final_v2} ({dur:.2f}s)")

log("全部完成")
