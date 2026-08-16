# creator-skills

Content-creation skill suites for AI agents — install the whole collection with one command, then pick the suites (or individual skills) you want.

Four suites, fourteen skills:

| Suite | Skills | What it does |
|---|---|---|
| **video-localization** | `video-cooking`, `video-download`, `video-subtitle`, `video-dubbing` | Bring an existing video over the language barrier: download it, transcribe, subtitle, and optionally re-voice it in Chinese. |
| **video-production** | `video-forge`, `tts-forge`, `remotion-4k-polish` | Produce an original video from source material: planning, provider-agnostic voiceover, and 4K render polish. |
| **image-text-cards** | `paged-article`, `xhs-cards`, `article-illustration` | Turn articles and posts into vertical 3:4 image-text card decks for Xiaohongshu (小红书). |
| **novel-promotion** | `fanqie-scout`, `novel-copywrite`, `generate-source-video`, `narrate-video` | Scout novels worth promoting and produce the promo video: selection, copywriting, source assembly, narration. |

The skill source repositories stay canonical — this repo is only the storefront. A [GitHub Action](.github/workflows/sync.yml) re-syncs it from the sources every 6 hours, so what you install is at most six hours stale.

## Install

### Any agent — skills CLI (recommended)

```bash
npx skills add ChHsiching/creator-skills
```

The picker shows the skills grouped by suite; select across suites freely. Use `-g` to install to `~/.agents/skills` (all your projects) instead of the current project, `--skill <name>` to skip the picker.

> The first install clones the whole repo (~80 MB — the image-text suite ships its rendering fonts). On a slow connection, prefix the command with `SKILLS_CLONE_TIMEOUT_MS=600000` if the clone times out.

### Claude Code — plugin marketplace

```
/plugin marketplace add ChHsiching/creator-skills
/plugin install video-localization@creator-skills
```

One plugin per suite.

### ZCode — plugin marketplace

Settings → Plugin Management → Discover → **`+`** → add `https://github.com/ChHsiching/creator-skills`, then install a suite from the list.

### Codex — plugin marketplace

```bash
codex plugin marketplace add ChHsiching/creator-skills
```

### External dependencies

Two skills lean on other people's repositories. They are intentionally **not** vendored here — install them separately if you need them:

| Needed by | Dependency | Install |
|---|---|---|
| `video-forge` (optional) | [`remotion-video-director`](https://github.com/BayramAnnakov/remotion-video-director) — from-scratch motion design | `npx skills add BayramAnnakov/remotion-video-director` |
| `xhs-cards` (required) | [`beautiful-article`](https://github.com/ConardLi/garden-skills/tree/main/skills/beautiful-article) — the editorial engine it routes over | `npx skills add ConardLi/garden-skills/skills/beautiful-article` |

Some skills also assume CLI tools on your machine (e.g. the video suites use [`cook`](https://github.com/ChHsiching/video-cook) and `ffmpeg`); each skill's SKILL.md says exactly what it needs.

## Use

Each skill is self-documenting: open its `SKILL.md`, or just invoke it by name in your agent (`/video-cooking <url>`, `/xhs-cards <article>`, …). The suites are independent — you can install and use any of them on its own.

To develop a skill, go to its source repository (linked from each skill directory), not this repo: changes here are overwritten by the sync Action.

## License

[MIT](LICENSE) for this repository's scaffolding. Each vendored skill carries its source repository's license in its directory where the source repo has one.

## Repo layout

```
skills/<suite>/skills/<skill>/…     vendored skill payloads (auto-synced — do not edit here)
.claude-plugin/marketplace.json     skills CLI grouping + Claude Code + Codex marketplace
marketplace.json                    ZCode marketplace
skills/<suite>/.{claude,zcode,codex}-plugin/plugin.json   per-suite plugin manifests (native form per host)
scripts/mapping.tsv                 the group/skill/repo mapping — single source of truth
scripts/sync.sh                     clone + vendor + regenerate manifests (local & CI)
```
