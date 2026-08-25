# xhs-cards

把任意链接、文件或粘贴的材料，变成一套 3:4 小红书图文卡片（1080×1440 设计画布 → 3240×4320 高清 PNG），外加一份可直接发布的小红书文案（caption）。

独立 skill，底层直接使用 [reacticle](https://github.com/ConardLi/reacticle) 组件库的 11 套主题；卡片排版由 agent 在固定的框架契约内按主题与内容**自由设计**，不套模板。

## 功能

- **从素材到成卡一条龙**：源抓取（含追链核实）→ 编辑规划（卡组清单 + 检查点确认）→ 工程脚手架 → 全部卡片设计 → 自动化审计 → 3x 渲染 → caption 撰写
- **框架内自由设计**：画布契约、字号地板、审计锚点是固定的；版式、字体搭配、装饰语言每副卡组重新设计
- **按主题就绪的脚手架**：`scaffold-deck.sh` 生成 deck 形态工作区，`index.html` 已按所选主题加载字体
- **原子化质量审计**：`verify.mjs` 一条命令跑完 typecheck/build/溢出/空洞/孤字换行/专名拆行/坏图/圆角/导出尺寸检查，输出单一 pass/fail
- **双循环审查**：排版循环（语义换行纪律）+ 文案循环（no-ai-slop 检测），另加含"冷读者"受众视角的终审
- **一次性交付**：全部卡片+验证+caption 完成后整体呈交，用户只审一次

## 安装

```bash
npx skills add ChHsiching/xhs-cards-skill
```

### 前置依赖

| 依赖 | 用途 | 安装 |
|---|---|---|
| [no-ai-slop](https://github.com/ChHsiching/no-ai-slop) | 文案审查循环（Step 6） | `npx skills add <owner>/no-ai-slop` |
| Node 18+ / npm | 卡片工作区（reacticle + Vite） | 自行安装 |
| chromium（playwright） | 渲染与审计 | `npx playwright install chromium`（playwright-core 由脚手架作为工作区依赖安装） |
| Python + Pillow | 像素级审计（空洞/尺寸） | `pip install pillow` |
| perl | 脚手架主题/字体注入（Git Bash 自带） | 一般无需单独安装 |

## 使用

在你的 agent（Claude Code、Codex 等支持 skills 的均可）里直接说：

> 用 xhs-cards 把这篇文章做成小红书图文：\<链接或文件\>

管线细节见 [SKILL.md](SKILL.md)。

## 仓库结构

```
xhs-cards-skill/
├── SKILL.md                    ← 管线（8 步）与依赖
├── references/
│   ├── themes.md               ← 11 套主题选型表 + 字体映射 + token 纪律
│   ├── card-anatomy.md         ← 固定框架契约（画布/锚点/字号地板）+ 截图原则
│   ├── typography.md           ← 语义换行纪律（排版循环规则集）
│   ├── pitfalls.md             ← 10 个实测踩坑与修复
│   ├── export.md               ← 验证与导出（verify / export-png）
│   └── caption-spec.md         ← 文案规范（1000 字正文/冷读者标题/字数验证）
├── scripts/
│   ├── scaffold-deck.sh        ← 一键生成 deck 工作区（按主题注入字体；--theme 必填）
│   ├── verify.mjs              ← 原子化审计（DOM + 像素）
│   ├── pixel_audit.py          ← PIL 像素审计（verify.mjs 调用）
│   └── export-png.mjs          ← 3x 渲染（卡数自动检测）
└── assets/
    ├── deck-template/          ← 脚手架使用的最小工程模板
    └── samples/                ← 往期成品卡组样例（仅参考，非模板）
```

## License

MIT
