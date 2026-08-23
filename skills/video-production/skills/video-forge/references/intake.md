# Intake guide

How to run the six-question interview, and the director brief that comes out of it.

## Scope questions vs shape questions

Shape questions are the director's (see SKILL.md's boundary) — they live in its Phase 1 list; never pre-ask or mirror them here.

Your scope-side categories:

| # | Category | What to settle | Session-proven example phrasings |
|---|---|---|---|
| 1 | Scope | full / highlights / full + short clips | "59 分钟完整" vs "5-10 分钟精华" |
| 2 | Subtitles | language(s), burn-in vs soft-sub files | bilingual / Chinese-only / English-only |
| 3 | Form | which visualization forms THIS material supports | derive from YOUR read of the material — what does IT suggest? |
| 4 | Audience & wording red lines | beginner vs expert; terminology handling; density preference | "观众是小白，先人话后术语，禁缩词怪词" and/or "不要空白等待，任意 N 秒窗口至少一次视觉事件" — record density as a number if given |
| 5 | Platform & specs | which platforms, resolution/fps | decides variants (bilibili triple card? xiaohongshu cover?) and render target |
| 6 | Voiceover | only for silent material | route choice → API key → voice audition, hand to tts-forge; **timing authority** — the timeline follows measured TTS audio (default, "audio-first") or design-estimated frames |

Two phrasing rules earned the hard way:

- **Form options must be derived from the material, every time.** A fixed menu fits last project and betrays this one. Read the transcript/article first, then design 2-3 genuinely different forms it supports, presented with ASCII previews.
- **Use the structured question tool with previews.** Users choose between concrete variants decisively and answer open prose vaguely. When they answer a form question with extra requirements ("very good, but make it dense, assume beginners"), those rider requirements are intake gold — record them in the brief.

## The director brief

One page, handed to remotion-video-director as it enters its Phase 2. Fields:

```
MATERIAL   what the source is; duration/length; author + URL for attribution
SCOPE      full/highlights answer; clip list if any
AUDIENCE   who watches; wording level; terminology rules (what stays English and why)
RED LINES  density (as a number if given); tone rules; anything the user vetoed
SUBTITLES  language(s); burn-in or soft
FORM       chosen visualization form + why the material supports it
PLATFORMS  target platforms; resolution/fps; required variants (e.g. bili triple card)
FACTS      verified key numbers/claims for on-screen use; UNVERIFIED list if any
ASSETS     speaker avatars/photos, source images, logo — what exists, what's cleared
AUDIO      original track / TTS plan (tts-forge output) / none — for TTS, the timing authority settled at intake (audio-first default or design-first)
```

The brief pre-answers the director's Phase 1 discovery (its Step 1) — say so when handing off. The director still runs its own Creative Direction, Reference, and Creative Brief steps (shape), which consume the brief and flow into Phase 2.
