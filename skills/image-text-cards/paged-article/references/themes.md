# themes.md — 主题 token 速查表（derived snapshot）

每个主题的 CSS token（hex 值 + 字体栈 + Google Fonts 链接），用于渲染分页时硬编码进每页的 `<style>`。

**来源**：这些值派生自 reacticle 组件库的运行时 CSS（`node_modules/reacticle/src/theme/themes/<id>/<id>.css`）。主题选择和设计理念看 [`../theme-profiles/index.json`](../theme-profiles/index.json) + 各 profile——那是权威来源；本文件只是渲染时的 token 速查。如果 reacticle 更新了主题值，以运行时 CSS 为准。

字细问题：衬线主题（press/bodoni/tufte/knuth）笔画有粗细变化，在 1x 下发虚——但 3x 渲染下不是问题。无衬线主题（vignelli/freddie/shannon/bayer/sottsass/andy）笔画均匀，天然清晰。

---

## press（书卷 / 编辑）★ 本次验证过

Stripe Press 那种出版物感。衬线正文，氧化血红只点结构。

```css
--bg:#fbf7ee; --fg:#211e18; --heading:#171410; --muted:#6a6256; --faint:#97907f;
--border:#e0d6c0; --border-strong:#cdc1a6; --surface:#f3ecdd;
--accent:#7b1e22; --accent-soft:#f0e2df;
--serif:'Newsreader','Source Serif 4',Spectral,Georgia,'Songti SC','STSong',serif;
--mono:'JetBrains Mono','SF Mono',Menlo,Consolas,monospace;
```
Google Fonts: `Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600;6..72,700`
- 气质：证据、克制、低装饰
- 禁止：圆角、阴影、色块卡片
- 字重建议：正文 500、标题 700、标签 600

## freddie（Mailchimp 暖黄 / 友善）★ 本次验证过

白底 + 明黄荧光高亮（黄是高亮不是文字色）。无衬线正文最清晰。

```css
--bg:#ffffff; --fg:#2c241c; --heading:#1d160f; --muted:#6f6356; --faint:#9c9081;
--border:#e7dfce; --border-strong:#d6ccb4; --surface:#f7f4ec;
--ink:#241c15; --yellow:#ffe01b; --yellow-soft:#fff1ad;
--serif:'Fraunces','Cooper Lt BT',Georgia,'Songti SC',serif;   /* 标题 */
--sans:'Hanken Grotesk','Inter','Helvetica Neue','Arial','PingFang SC',sans-serif;  /* 正文 */
--mono:'JetBrains Mono','SF Mono',Menlo,Consolas,monospace;
```
Google Fonts: `Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700` + `Hanken+Grotesk:wght@400;500;600;700`
- 气质：机灵、亲切、有人味
- 标志手法：黑字 + 黄 highlight（像荧光笔）、黄底贴纸章节号（轻微旋转）

## vignelli（瑞士国际主义文档）

唯一的冷中性 sans 正文主题。瑞士红点睛。

```css
--bg:#f6f7f8; --fg:#1a1c1e; --heading:#0d0f11; --muted:#5b6166; --faint:#8b9197;
--border:#d4d8db; --border-strong:#bcc2c6; --surface:#eceeef;
--accent:#d6201f; --accent-strong:#a81816;
--sans:'Söhne','Aktiv Grotesk','Inter','Helvetica Neue','Arial','PingFang SC',sans-serif;
--mono:'Söhne Mono','JetBrains Mono','SF Mono',Menlo,Consolas,monospace;
```
Google Fonts: `Inter:wght@400;500;600;700`
- 气质：冷、系统化、可扫读
- 标题和正文用同一字族，靠字号建层级

## bodoni（报刊 / Didone 高反差）

标题 Playfair Display 900 极粗，正文 Source Serif 4。近黑白。

```css
--bg:#fdfdfb; --fg:#16140f; --heading:#0a0908; --muted:#6f6356; --faint:#9c9081;
--border:#e0d6c0; --border-strong:#cdc1a6; --surface:#f3ecdd;
--accent:#0a0908;   /* 强调用黑，红只在风险处 */
--serif-heading:'Playfair Display','Bodoni 72','Didot','Songti SC',serif;
--serif-body:'Source Serif 4','Newsreader',Georgia,'Songti SC',serif;
--mono:'JetBrains Mono','SF Mono',Menlo,Consolas,monospace;
```
Google Fonts: `Playfair+Display:wght@700;900` + `Source+Serif+4:opsz,wght@8..60,400;8..60,600`
- 气质：戏剧、权威、大报特稿
- 标题字重 900，分量最足

## andy（柔软 / 治愈）

暖奶油底 + 暖橙，通体圆体（Nunito）。大圆角 + 柔阴影。

```css
--bg:#fff7ef; --fg:#443d36; --heading:#2a2420; --muted:#7a6e62; --faint:#a89c8e;
--border:#f0e6d8; --border-strong:#dbcbb5; --surface:#f9efe2;
--accent:#e0590b;   /* 暖橙 */
--sans:'Nunito','Quicksand','Helvetica Neue','PingFang SC',sans-serif;
--mono:'JetBrains Mono','SF Mono',Menlo,Consolas,monospace;
```
Google Fonts: `Nunito:wght@400;600;700;800` + `Quicksand:wght@500;600;700`
- 气质：柔软、平静、亲和
- 允许圆角（6-16px）和柔阴影

## shannon（暗底工程证据）

深炭底 + 琥珀金。暗色主题，小红书上最吸睛。

```css
--bg:#1a1916; --fg:#e8e4d8; --heading:#f4f1e8; --muted:#a8a294; --faint:#7a7468;
--border:#3a3833; --border-strong:#4d4a42; --surface:#252320;
--accent:#e0a73e;   /* 琥珀金 */
--sans:'IBM Plex Sans','Söhne',ui-sans-serif,system-ui,'PingFang SC',sans-serif;
--mono:'IBM Plex Mono','JetBrains Mono','SF Mono',Menlo,Consolas,monospace;
```
Google Fonts: `IBM+Plex+Sans:wght@400;500;600;700`
- 气质：暗色、工程现场、仪表感
- 注意：暗底配图需调整 SVG 颜色

## bayer（包豪斯 / 三原色几何）

暖白底，三原色当结构色（蓝章节号、红刊头、黄点睛）。

```css
--bg:#f4f0e6; --fg:#1b1a16; --heading:#100f0c; --muted:#6b6657; --faint:#9c9582;
--border:#d9d2c0; --border-strong:#c4baa3; --surface:#ede6d4;
--accent:#1f49c0;   /* 宝蓝 */
--sans:'Poppins','Hanken Grotesk','PingFang SC',system-ui,sans-serif;
--mono:'JetBrains Mono','SF Mono',Menlo,Consolas,monospace;
```
Google Fonts: `Poppins:wght@400;500;600;700` + `Josefin+Sans:wght@500;600;700`
- 气质：响亮、理性、几何构成

## sottsass（孟菲斯 / 80s 撞色）

暖白底，电光蓝 + 撞色粉彩。最叛逆好玩。

```css
--bg:#fcf7ef; --fg:#1a1714; --heading:#0e0c0a; --muted:#6f6356; --faint:#9c9081;
--border:#e8dfcc; --border-strong:#d4c8ac; --surface:#f5eee0;
--accent:#2c54e0;   /* 电光蓝 */
--sans:'Hanken Grotesk','PingFang SC',system-ui,-apple-system,sans-serif;
--serif-heading:'Space Grotesk','Hanken Grotesk','PingFang SC',system-ui,sans-serif;
--mono:'JetBrains Mono','SF Mono',Menlo,Consolas,monospace;
```
Google Fonts: `Hanken+Grotesk:wght@400;500;600;700` + `Space+Grotesk:wght@500;600;700`
- 气质：叛逆、好玩、80s

---

## 通用结构组件（所有主题共享）

无论选哪个主题，以下 HTML 结构 class 名固定（方便复用）：

| 组件 | class | 用途 |
|---|---|---|
| 水印 | `.watermark` | 右下角大字低透明度背景 |
| 顶部标签 | `.eyebrow` / `.kicker` | 血红/主色小字 + 宽字距 |
| SVG 主视觉 | `.hero` | 封面中间的图解区 |
| 标题区 | `.title-block h1` | 封面大标题 |
| 引导句 | `.lead` | 标题下、正文前的引导（左竖线） |
| 正文段 | `.body p` | 主谓宾完整段落 |
| 核心判断块 | `.aside` | 浅底 + 左色条 + UPPERCASE 标签 |
| 对比表 | `.compare` | 双栏 grid，左右发丝线分隔 |
| 引用块 | `.quote` | 左竖线 + 英文原文 + 出处 |
| 要点列表 | `.points li` | 破折号/色块前缀 |
| 页眉 | `.header .ch-num / .ch-name` | 大序号 + 章节名 |
| 页脚 | `.footer .pg` | 发丝线 + 页码 |

颜色/字体用主题 token 变量填充；结构 class 名不变。
