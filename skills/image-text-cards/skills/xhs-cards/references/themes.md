# Themes

The 11 reacticle themes, internalized for card decks (sourced from reacticle `src/theme/themes/` + authoring profiles; re-sync when reacticle ships new themes). CSS lives in the workspace at `node_modules/reacticle/src/theme/themes/<id>/<id>.css` — read it for the exact tokens; never hardcode hex values from memory.

## Choosing

Pick by **content fit first**: the theme's character should map to the material's character (a Memphis theme for playful content, an ink-and-evidence theme for benchmarks). Warm themes (andy / freddie / sottsass) generally suit Xiaohongshu. Engineering convenience ("templates exist for it") is never the lead argument.

## Per-theme table

Fonts/links: the **source of truth is `scripts/scaffold-deck.sh`** — it injects each theme's Google Fonts link (mono included) into the generated `index.html`. The table below lists the character-defining display fonts only; consult the script for the full load list.

| id | character | fits | main webfonts | notes for cards |
|---|---|---|---|---|
| andy | 静谧温柔，暖奶油+暖橙，大圆角柔影 | healing, onboarding, lifestyle | Quicksand, Nunito | accent `--hs-orange` (fills only) |
| freddie | 暖黄黑字，机灵有人味，俏皮衬线 | explainers, tutorials, FAQ | Fraunces, Hanken Grotesk, Inter | highlighter-yellow fills |
| sottsass | 孟菲斯 80s 撞色，硬投影+旋转药丸+彩屑 | playful explainers, launches, culture | Space Grotesk, Hanken Grotesk, JetBrains Mono | pink/teal/yellow fill-only (`--st-*`); cobalt carries readable structure |
| bayer | 包豪斯三原色几何，响亮理性 | manifestos, product intros | Josefin Sans, Poppins, Hanken Grotesk | primary colors as structural color |
| press | 书卷编辑感，温暖叙事 | essays, briefings | Newsreader, Source Serif 4, Spectral | long-form mood |
| tufte | 证据/数据/克制，墨色线条 | benchmarks, evidence-heavy decks | — (system serif) | line-not-box; two data colors |
| shannon | 暗底工程现场，仪表信号 | postmortems, system internals | IBM Plex Sans, IBM Plex Mono | dark bg — check PNG corners & contrast |
| vignelli | 瑞士网格，冷中性 sans | specs, docs | Inter, JetBrains Mono | grid discipline |
| knuth | 学术预印本，编号公式 | papers, research digests | Source Serif 4 | formal numbering |
| bodoni | 黑白高反差大刊 | manifests, essays | Playfair Display, Source Serif 4 | dramatic covers |
| fuller | 蓝图工程制图 | specs, system design | IBM Plex Sans | drawing annotations |

## Token discipline

- Text/structure colors: `--ra-color-*` (text, heading, muted, border, border-strong, accent…).
- Theme-local accents (andy's `--hs-orange`, sottsass's `--st-pink/teal/yellow/blue`): fills and decorations only — never small-text or link colors; readable structure stays on `--ra-color-accent`.
- Shadows follow the theme's language (sottsass: hard offset, zero blur; andy: soft). Copy the pattern from the theme CSS, don't invent cross-theme hybrids.
- Theme display weights cap at what the webfont provides (e.g. Space Grotesk has no 800).

## After scaffold

`index.html` already loads the right fonts. If you swap themes mid-run, re-run the font link swap from `scripts/scaffold-deck.sh`'s `fonts_for()` and change `<ThemeProvider theme="…">` in `article/main.tsx` — two places, both required.
