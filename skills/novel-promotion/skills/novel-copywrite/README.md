# novel-copywrite-skill

A [skill](https://github.com/anthropics/agent-skills) for AI coding agents (Claude Code, Cursor, etc.) that turns a scouted novel into a **promotion work order** — a 4-char alias + a 30-second hook script + a 3-minute full script.

Give it a `scouted.json` from [fanqie-scout](https://github.com/ChHsiching/fanqie-scout-skill), and it:
1. Reads the novel's first 5 chapters
2. Picks the 3 consecutive chapters with the densest conflict
3. Suggests a 4-char promotion alias (common characters only)
4. Writes a **hook script** (30s, ~150 chars) following a 6-beat structure
5. Writes a **full script** (3min, ~1000 chars) expanding the 3 chapters
6. Outputs a markdown work order ready for [novel-promo](https://github.com/ChHsiching/novel-promo-skill)

## Architecture

```
scouted.json (from fanqie-scout)
   ↓
[agent] reads 5 chapters, picks 3, determines person/tense
   ↓
[agent] suggests 4-char alias
   ↓
[agent] writes hook (6-beat structure) + full script (chapter expansion)
   ↓
work-order.md → ready for novel-promo
```

This skill is **pure agent work** — no scripts. The agent reads the novel, applies the hook formula (documented in SKILL.md with a full example in `references/`), and writes the scripts.

## Hook structure (the core innovation)

The 30-second hook follows 6 beats, in order:

1. **Scene image** — where, what (sensory)
2. **Counterparty description** — who, visual
3. **Counterparty's attitude** — hostile? afraid?
4. **Core conflict reveal** — the stakes, the payload
5. **Protagonist's reversal** — breaks expectations
6. **Cliffhanger + "..."** — cut mid-action

See `references/example-nieqian.md` for a complete annotated example.

## Install

```bash
npx skills add ChHsiching/novel-copywrite-skill
```

## Prerequisites

- A `scouted.json` from [fanqie-scout](https://github.com/ChHsiching/fanqie-scout-skill) (contains book metadata + first 5 chapters)

## Usage

```
/novel-copywrite <scouted.json path> [book_id]
```

## License

AGPL-3.0-only · Copyright (c) 2026 ChHsiching —— 见 [LICENSE](LICENSE)。

- 使用（含公司内部使用）、修改、分发均免费；但分发或以本代码提供网络服务时，衍生作品须以 AGPL-3.0 开源。
- 闭源商用须另行获取商业授权：hsichingchang@gmail.com

### 贡献条款

提交 PR 即表示你同意以 AGPL-3.0 授权你的贡献，并授予维护者在 AGPL 之外另行提供商业授权的权利（你的贡献始终以 AGPL 对所有人开放）。
