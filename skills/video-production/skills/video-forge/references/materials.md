# Material pipelines

Per-type processing, the review gates, and the verification mechanics.

## Audio / video material

### Transcription environment (shared, upgraded)

cook and whisperx live in ONE persistent shared Python environment — installed once, reused by every project. Never pip-install whisperx/torch per-project (torch alone is ~2GB); model caches under `~/.cache/huggingface/hub/` and `~/.cache/torch/hub/` are shared across projects for free.

1. **Resolve the shared environment**, in order: a `VIDEO_TOOLS_VENV` env var (explicit override) → `~/.venvs/video-tools/` (the conventional location) → the system Python (if cook is pip-installed there). Invoke cook via that environment's absolute binary path — the agent computes the path; the user's PATH does not matter.
2. **Upgrade before first use in a run** — idempotent, the agent's job (the user never thinks about cook's version): `pip install -U "video-cook[all]"` in the shared env (the `[all]` extra carries whisperx). A version NUMBER is the wrong check; probe the subcommands this run needs by exit code instead: `cook transcribe --help` parses = good.

### Transcription run

1. **Transcribe** via the `cook` CLI (`cook transcribe <root> <name>` — foreground by default: pass `--detach` when running it from a terminal directly, or leave it foreground under a host background task; either way it writes a pollable log and emits the en.srt). Whole file in one call — chunking breaks sentence alignment. Without the cook CLI installed, run whisperx directly with the same whole-file rule and manage backgrounding yourself. CPU large-v3 with VAD runs in the neighborhood of realtime (measure on the first run — this figure moves with the CPU) — run it detached or backgrounded and do intake meanwhile.
2. **AV sources that are "video"**: check a few far-apart frames before assuming motion — official podcast uploads are often a single static frame plus audio, which changes the whole design (and frees you from video decode in every render).

## URL / article material

- Fetch the page; JS-rendered pages return empty via plain fetch — drive a real browser bridge.
- Capture source metadata (author, title, URL, publish date) for attribution and later fact-checking.
- Run a research subagent on the topic to collect verifiable facts, numbers, and proper-noun spellings BEFORE any text goes on screen. Anything the research cannot confirm from an authoritative source is UNVERIFIED — surface it to the user, never silently render it.
- When the video is itself a curation of third-party items (a roundup, a top-N, an ecosystem guide), the candidate pool is built by the Curation discovery protocol below — run it before the pool freezes.

## Curation discovery (roundup / recommendation material)

When the video curates a set of third-party items (plugins, tools, models, repos), the candidate pool is a discovery product, not a copy of the seed article. Two failure classes, both from a real production: a 92k-star project excluded on a README-only read (its integration lived in `docs/agent-adapters.md`, and one wrongly-excluded taskboard shipped a standard plugin in `integrations/` while both of its READMEs never mentioned it) — and a memory product that never entered the pool at all (its official integration blog was the top web hit for the category, but discovery had only searched registries).

**Breadth — four source axes before the pool freezes:**

1. **Ecosystem registries, enumerated**: enumerate the main registry/marketplace category pages in full and diff against the pool. A registry used only as a stats source catches nothing.
2. **Category web search**: plain search-engine queries for `<ecosystem> <category>`. Registry and topic-tag search is blind to projects that integrate without self-tagging.
3. **2-3 aggregator roundups**: third-party articles/stores overlap imperfectly with registries; sweep at least two.
4. **The seed material**: what the user handed over is one source of candidates, never the pool itself.

**Admission bar**: actively maintained + substantial stars + actually working, all three verified. Maintenance frequency is the hard one in fast-breaking ecosystems — a high-star stalled project is a time bomb; cut it.

**Exclusion correctness — a "no integration" verdict is a negative claim; prove it wider than you would an admission:**

- Four checks, all of them, before writing "zero integration": ① repo full text — README is just the entry point (also `docs/`, `integrations/`, package manifests); ② the project's own docs site (agent-integration pages); ③ package-registry reverse lookup under the org's scope; ④ community-registry full-text search for the project name.
- Auto-aggregated stores (topic scrapers) prove nothing — listed ≠ integrated.
- High stars × target category = mandatory deep pass through all four checks; those are exactly the projects a shallow read wrongly excludes.
- Log every exclusion in the research notes with the same rigor as an admission (checks performed, search terms, date) — verdicts must be overturnable later.
- Control check: known-true integrations from previous runs should be findable in the main verified registry; if they are, that registry is your highest-discrimination check.

**Recall audit before publish**: re-run the four axes and diff against the final list; any new high-star hit gets the four checks before shipping. Fast-moving ecosystems change weekly, and a viewer comment is the most expensive place to discover a miss.

**A post-publish miss is a rule update, not just a reply** — the correction lands in this protocol the same day: add the failure mode, sharpen the check that would have caught it.

## Screenshot capture (web pages as evidence frames)

- **Zoom by narrowing the emulated viewport, not by page CSS zoom**: emulating 960×540 at DPR 4 reproduces 200% browser zoom at full 4K pixel count. Page-level CSS zoom overflows centered layouts — the capture lands on the top-left corner plus a scrollbar.
- **Centered cards**: capture the full viewport, read the card's bounding box, crop from the capture.
- **Crop the scrollbar strip** off the right edge — it appears at any zoom once the page scrolls.
- **Place at natural aspect**: an image enters a card at full width and its own height. `objectFit: cover` zooms and crops silently — background use only, after the user has seen the crop.
- Manual user-set browser zoom stays the fallback when the user wants specific framing.

## Gate mechanics (all gates)

- **Round structure**: fresh subagent reads every cue end-to-end, checks every proper noun in context (web-searching anything it questions), reports numbered defects → router fixes each by hand → new fresh subagent reruns the FULL read. Repeat until a round reports zero. Spot-checking fixed lines is not a pass; the fix itself can introduce defects. Scale to the material: a 10-cue short needs one full pass per gate, not subagent loops.
- **Alignment blind spot**: count-only verifiers (n cues = n lines) pass while every line is off by one. Always also compare timestamps byte-for-byte against the source SRT, and spot-read EN[N]↔ZH[N] pairs at intervals.
- **Silence hallucinations**: a tiny-duration cue landing on silent audio is a hallucination — check the cue's window against the audio energy (RMS near zero) before trusting or deleting it, then delete and renumber; a hallucinated cue poisons translation counts and every downstream alignment check.
- **Real-word mishears**: proper-noun web checks miss real-word substitutions (split "pains"→"panes", "their IDs"→"IDEs", a product name heard as a common word) — reviewers read each cue against its topic context, and when the speaker later self-corrects or re-mentions the term, that later cue is the confirmation source.
- **Fix log discipline**: log every fix as `<ASR output> → <correct form> — how confirmed` (glossary / official page / web / context), and keep an explicit checked-keeps list (speaker coinages, spoken forms that differ from the reference material) — without it, later review rounds "fix" deliberate forms back into errors.

## Terminology gate (all on-screen text; translation follows when subtitles are bilingual)

- **Terminology**: ecosystem vocabulary the audience would look up stays in English (skill names, tool names, system terms like `spec`/`agent`/`ticket`); everyday words translate. When a term is both (e.g. a tool's tickets vs generic tickets), keep the ecosystem term English and gloss it in Chinese at first mention.
- **Cue boundaries**: commands, shortcuts, product names are atomic — never split across cues. Chinese follows Chinese sentence boundaries, not the English cue grid.

## AI-flavor gate (all on-screen text)

Runs as a multi-axis subagent loop: one axis per round, a fresh subagent doing the full read each time, repeated until a round reports zero — the loop guards both directions (an under-edited draft and an over-edited one). Two axes need no pattern list because they are generative judgments.

**Axis 1 — pattern defects (external skill, detect mode).** Load `no-ai-slop` (probed in Step 0) and run its detect mode over subtitles, cards, covers, and publish copy. Wrap the call for non-English copy: apply its editing principles and pattern sections, skip its English word lists, report findings in the working language. Each finding names the pattern, quotes the line, and gives a one-line fix. Fallback when the skill is missing — hunt locally: machine-compound words nobody says aloud; translated-English constructions (inverted negation, adverb-fronted praise); stock LLM phrasing, filler transitions, lists of exactly three; card text relying on auto-wrap (break at semantic units instead); vague quantifiers where the verified fact is a specific number ("很多问题", "数十万").

**Axis 2 — generative criteria (register-level slop no pattern list catches).** Judge per line:
- *Portability*: a line that would read unchanged in anyone's video about any product is filler — replace it with a fact, number, mechanism, or judgment specific to this subject.
- *Specificity*: abstract praise ("significantly improves…") becomes the concrete figure from the verified facts list.
- *Spoken-aloud test* (narration): narration is written to be read aloud; if a native speaker wouldn't say the line at that pace, it fails — whatever its language mix. The failure is sounding machine-generated, never the presence of any particular language.

**Axis 3 — voice preservation (the over-editing brake).** Diff the draft against the previous round: fixes that sand off personality, humor, deliberate rhythm, or the author's phrasing are defects on this axis. The bar is "reads like a person", and generic-polished prose fails it.

Hand-fix per finding and log What-changed (pattern → fix → flagging axis). Attach the keep-English glossary so approved terms survive axis 1.

## Fact verification checklist

Every number, claim, name, and quote destined for the screen gets cross-checked against an authoritative source (official repo, primary article, the author's own docs). Where docs/README and the implementation disagree, the implementation wins — one production found three README-vs-code mismatches this way. Verified facts carry their source; the rest are UNVERIFIED. Fast-moving numbers (stars, installs) change between recording and publish — when both values appear on screen, stamp each with its as-of date so the card can't read as a contradiction. Numbers read out of an image (screenshot text, OCR, vision-model reads) are UNVERIFIED until re-checked against a text source or API — vision models misread digits. The storyboard stage should only use the verified list.

## Images

Inventory as supplementary assets (avatars, references, raw material). An image set alone is rarely a video's sole content — confirm intent during intake before planning around it.
