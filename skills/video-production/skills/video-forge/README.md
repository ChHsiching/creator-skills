# video-forge

Turn any raw material — a URL, article, image set, podcast episode, or video file — into a finished, publishable video.

`video-forge` is the **router**: it runs the intake interview (scope, subtitles, visualization form, audience red lines, platforms, voiceover + timing authority), processes your material until it's build-ready (transcription with multi-round review gates, fact verification, translation), then hands a complete brief to [`remotion-video-director`](https://github.com/BayramAnnakov/remotion-video-director), which owns the creative build. Delivery comes back under `video-forge`'s playbook as four machine-checked gates — stills approval, spec-checked render with audio, content gates (loudness / blank-scene sweep / neutral vision reads), then the 4K final with covers, platform variants, and publish copy.

The workflow was forged on real productions (a 59-minute podcast → 4K60 annotated visualization among them) and encodes the failures: count-only alignment checks that pass drifted subtitles, static-frame "video" sources, covers that pass pixel metrics but wrap their titles, endings that cost completion rate, hand-computed timing that drifts from the narration, and self-assessed "looks fine" checks that clear gates a machine would fail.

## Install

Skills — install all six; video-forge dispatches to the others by name at runtime:

```bash
# dependencies (third-party)
npx skills add BayramAnnakov/remotion-video-director   # required — the build engine
npx skills add remotion-dev/skills                     # required — official Remotion API series (37 rule files), the engine's knowledge base
npx skills add https://github.com/petergyang/no-ai-slop --skill no-ai-slop   # AI-flavor gate's pattern axis (inline fallback when missing)

# this ecosystem
npx skills add ChHsiching/video-forge
npx skills add ChHsiching/remotion-4k-polish           # required for 4K finals — text/line quality
npx skills add ChHsiching/tts-forge                    # required when silent material needs a voice
```

Tools (binaries, probed at runtime): `ffmpeg` on PATH; the [`cook`](https://github.com/ChHsiching/video-cook) CLI (`pip install video-cook[all]`) for AV transcription — whisperx-direct works without it, you just manage backgrounding yourself. Voiceover is provider-routed at runtime: MiniMax needs the `mmx` CLI (login + topped-up balance), OpenAI needs an API key — tts-forge collects whichever is needed when a voice is requested.

## Use

Just hand it material and say what you want:

> 把这期播客做成视频，mp3 在 ./ep88.mp3
>
> Make a video from this article: https://example.com/post

It interviews you (a few structured questions), grinds the material, shows you a check render, and ships the final cut with covers and publish copy.

## License

MIT
