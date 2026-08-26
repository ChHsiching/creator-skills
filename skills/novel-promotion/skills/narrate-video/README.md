# narrate-video-skill

A [skill](https://github.com/anthropics/agent-skills) for AI coding agents (Claude Code, Cursor, etc.) that adds **AI narration and burned-in subtitles** to a finished silent video.

Give it a script file and a silent video, and it produces a final video with:
- Sentence-level voiceover synthesized by [IndexTTS2](https://github.com/index-tts/index-tts) (B站开源, emotion-aware, voice-cloned)
- Burned-in subtitles with smart CJK line wrapping (semantic boundaries, jieba-assisted)
- Agent-reviewed subtitle line breaks (catches jieba mis-segmentation of proper nouns like 兰若寺)

## What it does

```
script.txt + silent video.mp4
   ↓
1. Split script into full sentences at 。！？
2. IndexTTS2 synthesizes each sentence (reads internal punctuation natively)
3. Generate sentence-level timestamps (one SRT cue per sentence)
4. Split each sentence for subtitle display:
   - Short → as-is
   - Long, no punctuation → jieba semantic split
   - Long, with punctuation → split at punctuation, then jieba any overflow fragment
5. Agent reviews line breaks (catches 兰若寺 → 兰若+寺 errors)
6. ffmpeg burns subtitles into video
   ↓
final.mp4 (video + voice + subtitles)
```

## What it does NOT do

- Does **not** generate the silent video itself — that's a sibling skill's job
- Does **not** write or edit the script — script is input, used verbatim
- Does **not** upload or publish anywhere

This skill is the **narration stage** in a larger novel-promotion pipeline. A future router skill orchestrates: script generation → material acquisition → silent video → **narrate-video** → publish.

## Install

```bash
npx skills add ChHsiching/narrate-video-skill
```

## Prerequisites

- [IndexTTS2](https://github.com/index-tts/index-tts) v2.5 installed locally (~10 GB models). On first run the skill searches common locations and asks once if not found, holding the path in memory for that run only.
- [uv](https://docs.astral.sh/uv/) for running Python in the IndexTTS2 env.
- [ffmpeg](https://ffmpeg.org/) on PATH.

## Usage

```
/narrate-video <path-to-video-subdirectory>
```

The subdirectory must contain:
- `script.txt` — the narration script (plain text, UTF-8)
- `video.mp4` — the silent source video

Output lands in `<subdir>/output/`:
- `audio.wav` — final narration
- `audio.srt` — sentence-level subtitles
- `subtitle.ass` — styled subtitles (post-review)
- `final.mp4` — the final product

## Reference voices

The skill ships one default voice (`voices/yunxi-male-fast.mp3` — a young male voice, slightly fast, suited for novel narration). Add more by dropping `.mp3`/`.wav` files into the skill's `voices/` folder.

## License

MIT
