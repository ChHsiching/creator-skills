# Material pipelines

Per-type processing, the review gates, and the verification mechanics.

## Audio / video material

### Transcription environment (shared, upgraded)

cook and whisperx live in ONE persistent shared Python environment — installed once, reused by every project. Never pip-install whisperx/torch per-project (torch alone is ~2GB); model caches under `~/.cache/huggingface/hub/` and `~/.cache/torch/hub/` are shared across projects for free.

1. **Resolve the shared environment**, in order: a `VIDEO_TOOLS_VENV` env var (explicit override) → `~/.venvs/video-tools/` (the conventional location) → the system Python (if cook is pip-installed there). Invoke cook via that environment's absolute binary path — the agent computes the path; the user's PATH does not matter.
2. **Upgrade before first use in a run** — idempotent, the agent's job (the user never thinks about cook's version): `pip install -U video-cook` in the shared env. A version NUMBER is the wrong check; probe the subcommands this run needs by exit code instead: `cook transcribe --help` parses = good.

### Transcription run

1. **Transcribe** via the `cook` CLI (`cook transcribe <root> <name>` — detaches itself, writes a pollable log, emits the en.srt). Whole file in one call — chunking breaks sentence alignment. Without the cook CLI installed, run whisperx directly with the same whole-file rule and manage backgrounding yourself. CPU large-v3 with VAD runs in the neighborhood of realtime (measure on the first run — this figure moves with the CPU) — launch it in the background and do intake meanwhile.
2. **AV sources that are "video"**: check a few far-apart frames before assuming motion — official podcast uploads are often a single static frame plus audio, which changes the whole design (and frees you from video decode in every render).

## URL / article material

- Fetch the page; JS-rendered pages return empty via plain fetch — drive a real browser bridge.
- Capture source metadata (author, title, URL, publish date) for attribution and later fact-checking.
- Run a research subagent on the topic to collect verifiable facts, numbers, and proper-noun spellings BEFORE any text goes on screen. Anything the research cannot confirm from an authoritative source is UNVERIFIED — surface it to the user, never silently render it.

## Gate mechanics (all gates)

- **Round structure**: fresh subagent reads every cue end-to-end, checks every proper noun in context (web-searching anything it questions), reports numbered defects → router fixes each by hand → new fresh subagent reruns the FULL read. Repeat until a round reports zero. Spot-checking fixed lines is not a pass; the fix itself can introduce defects.
- **Alignment blind spot**: count-only verifiers (n cues = n lines) pass while every line is off by one. Always also compare timestamps byte-for-byte against the source SRT, and spot-read EN[N]↔ZH[N] pairs at intervals.
- **Silence hallucinations**: a tiny-duration cue landing on silent audio is a hallucination — check the cue's window against the audio energy (RMS near zero) before trusting or deleting it, then delete and renumber; a hallucinated cue poisons translation counts and every downstream alignment check.
- **Real-word mishears**: proper-noun web checks miss real-word substitutions (split "pains"→"panes", "their IDs"→"IDEs", a product name heard as a common word) — reviewers read each cue against its topic context, and when the speaker later self-corrects or re-mentions the term, that later cue is the confirmation source.
- **Fix log discipline**: log every fix as `<ASR output> → <correct form> — how confirmed` (glossary / official page / web / context), and keep an explicit checked-keeps list (speaker coinages, spoken forms that differ from the reference material) — without it, later review rounds "fix" deliberate forms back into errors.

## Terminology gate (all on-screen text; translation follows when subtitles are bilingual)

- **Terminology**: ecosystem vocabulary the audience would look up stays in English (skill names, tool names, system terms like `spec`/`agent`/`ticket`); everyday words translate. When a term is both (e.g. a tool's tickets vs generic tickets), keep the ecosystem term English and gloss it in Chinese at first mention.
- **Cue boundaries**: commands, shortcuts, product names are atomic — never split across cues. Chinese follows Chinese sentence boundaries, not the English cue grid.

## AI-flavor gate (all on-screen text)

One dedicated pass over subtitles, cards, covers, and publish copy hunting:

- machine-compound words nobody says aloud (a coined "interrogation-meeting" style compound is the tell — replace with what a person would say)
- translated-English constructions (inverted negation, "arrive at a term", adverb-fronted praise)
- stock LLM phrasing, filler transitions, lists of exactly three
- card text relying on auto-wrap — break lines at semantic units instead
- vague quantifiers ("很多问题", "数十万") where the verified fact is a specific number — substituting the verified figure is part of this pass

Run it as its own fresh-subagent round with a keep-English glossary attached (so it flags real issues, not approved terms), then hand-fix line by line.

## Fact verification checklist

Every number, claim, name, and quote destined for the screen gets cross-checked against an authoritative source (official repo, primary article, the author's own docs). Verified facts carry their source; the rest are UNVERIFIED. Fast-moving numbers (stars, installs) change between recording and publish — when both values appear on screen, stamp each with its as-of date so the card can't read as a contradiction. The storyboard stage should only use the verified list.

## Images

Inventory as supplementary assets (avatars, references, raw material). An image set alone is rarely a video's sole content — confirm intent during intake before planning around it.
