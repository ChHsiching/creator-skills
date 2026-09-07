# remotion-4k-polish

Make 4K Remotion renders look right: smooth text edges, properly weighted hairlines, no moov-atom surprises.

Remotion's `--scale=2` rides Chromium's deviceScaleFactor=2 path, which disables font hinting — so 4K masters come out with jagged small text and vanishing hairlines while the 1080p draft looked great. This skill explains the root cause and gives you three paths:

- **B — 4K-native composition** (quality default for new projects): design at 3840×2160, render `--scale=1`, full rasterization quality
- **A — 1080p master + lanczos upscale** (universal quick path): best-possible text, one ffmpeg pass, ~4× faster render
- **C — scale=2 + line-weight/stroke compensation** (mitigation for existing setups, with an honest ceiling)

Plus line-weight compensation, serif stroke sizing, and post-kill file integrity checks.

## Install

```bash
npx skills add ChHsiching/remotion-4k-polish
```

No other skill required — it applies to any Remotion project. Needs `ffmpeg` (upscale path) and `ffprobe` (integrity checks) on PATH.

## Use

> 渲 4K 出来小字全是毛刺，怎么办
> 我要渲个 4K 成片，直接 scale=2 行吗

Load it before choosing 4K render settings, or after a rough render comes out. It picks the path that fits your project (size-parameterized theme → B; existing scale=2 master → C or A re-render) and gives exact commands — the second question above lands on the decision block, not a post-mortem.

## License

AGPL-3.0-only · Copyright (c) 2026 ChHsiching —— 见 [LICENSE](LICENSE)。

- 使用（含公司内部使用）、修改、分发均免费；但分发或以本代码提供网络服务时，衍生作品须以 AGPL-3.0 开源。
- 闭源商用须另行获取商业授权：hsichingchang@gmail.com

### 贡献条款

提交 PR 即表示你同意以 AGPL-3.0 授权你的贡献，并授予维护者在 AGPL 之外另行提供商业授权的权利（你的贡献始终以 AGPL 对所有人开放）。
