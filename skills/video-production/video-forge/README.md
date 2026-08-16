# video-forge

Turn any raw material — a URL, article, image set, podcast episode, or video file — into a finished, publishable video.

`video-forge` is the **router**: it runs the intake interview (scope, subtitles, visualization form, audience red lines, platforms, voiceover), processes your material until it's build-ready (transcription with multi-round review gates, fact verification, translation), then hands a complete brief to [`remotion-video-director`](https://github.com/BayramAnnakov/remotion-video-director), which owns the creative build. Delivery — check renders, 4K finals, covers, platform variants, publish copy — comes back under `video-forge`'s playbook.

The workflow was forged on real productions (a 59-minute podcast → 4K60 annotated visualization among them) and encodes the failures: count-only alignment checks that pass drifted subtitles, static-frame "video" sources, covers that pass pixel metrics but wrap their titles, endings that cost completion rate.

## Install

Skills — install all five lines; video-forge dispatches to the others by name at runtime:

```bash
npx skills add BayramAnnakov/remotion-video-director   # required — the build engine
npx skills add remotion-dev/skills                     # required — official Remotion API series (37 rule files), the engine's knowledge base
npx skills add ChHsiching/video-forge
npx skills add ChHsiching/remotion-4k-polish           # required for 4K finals — text/line quality
npx skills add ChHsiching/tts-forge                    # required when silent material needs a voice
```

Tools (binaries, probed at runtime): `ffmpeg` on PATH; the `cook` CLI (`pip install video-cook[all]`) for AV transcription — whisperx-direct works without it, you just manage backgrounding yourself.

## Use

Just hand it material and say what you want:

> 把这期播客做成视频，mp3 在 ./ep88.mp3
>
> Make a video from this article: https://example.com/post

It interviews you (a few structured questions), grinds the material, shows you a check render, and ships the final cut with covers and publish copy.

## License

MIT
