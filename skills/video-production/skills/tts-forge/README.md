# tts-forge

Provider-agnostic voiceover production: pick a TTS provider, audition voices for free, keep the spoken script and display text separate, then synthesize incrementally with the costs shown.

Built around the two ways voiceover goes wrong: burning synthesis quota to discover a voice is awful, and feeding TTS the display text so it reads out symbols and mangles product names. `tts-forge` auditions on free channels first, splits narration from display text, and resumes interrupted runs without re-spending.

## Install

```bash
npx skills add ChHsiching/tts-forge
```

No other skill required. Provider tools per route: `mmx` CLI for MiniMax (login `--region=cn` + account balance), `curl` + `OPENAI_API_KEY` for OpenAI, or any provider you wrap with three commands (audition / synthesize-segment / skip-existing).

## Use

> 这篇文章做成视频需要配音，帮我配
>
> Narrate this script, I want to hear voice options first

It interviews you for a provider (Chinese narration → MiniMax, quick start → OpenAI, free drafts → edge-tts, …), takes the key, plays voice options, and synthesizes per-segment with skip-existing resume.

## License

MIT
