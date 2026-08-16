# PITFALLS.md — 踩过的坑和解法

SKILL.md 的环境检查和各步骤可能踩到的坑。每条是「现象 → 根因 → 解法」，agent 遇到对应现象按这个查。

---

## 环境类

### `Cannot find package 'playwright'`（ESM 裸导入解析失败）

**现象**：render_page.mjs / lint_page.mjs 报 `ERR_MODULE_NOT_FOUND: Cannot find package 'playwright'`，即使 run 目录装了 playwright。

**根因**：ESM 裸导入（`await import('playwright')`）从**脚本所在目录**解析 node_modules，不是从 cwd。skill 脚本在 skill 目录，那里通常没装 playwright。

**解法**：脚本已改用 `createRequire` 从 cwd（run 目录）解析。确认 playwright 装在 run 目录：
```bash
cd <run-dir> && npm i playwright
```
然后从 run 目录调用脚本（脚本内部会从 cwd 找 playwright）。

---

### GLM-Image 尺寸报错（HTTP 400 / size not multiple of 32）

**现象**：zai 后端返回 400，或图片生成失败。

**根因**：GLM-Image 要求尺寸是 32 的倍数（512-2880 px 之间，总面积 ≤ 2²² px）。`1280x720` 的 720 不是 32 的倍数。

**解法**：传 `--size 1280x736`（736 = 32×23）做 16:9。GPT-image 没这个限制。

---

### API key 在 shell env 里找不到

**现象**：gen_image.mjs 报「No image provider」或「XXX_API_KEY not set」，但你在别处（.env 文件、OS GUI 环境变量、IDE 配置）设过。

**根因**：gen_image.mjs 读的是 `process.env`。key 在 `.env` 文件或别的工具的配置里，但没 export 到当前 shell 会话，node 看不到。

**解法**：source 进 shell，或 inline 传：
```bash
set -a; source /path/to/.env; set +a   # .env 里的变量 export 进来
node scripts/gen_image.mjs ...
```
别假设在别的工具（ZCode config、IDE）里设的 key 对 node 可见。

---

## 版面类

### 正文溢出画布（footer 被裁 / text 和 footer 重叠）

**现象**：渲染出的 PNG 底部内容被切掉，或 lint_page.mjs 报「BODY 溢出底部」「.text 与 .footer 重叠」。

**根因**：内容（段落 + codeblock + 列表）总高度超过插图分配后的剩余空间。

**解法**（按代价从低到高）：
1. **缩插图高度**：page.html 的 `ILLO_H` 字段从 600 调到 340-520（正文越长，插图越小）。lint 溢出就调小，lint 空旷就调大。
2. **精简正文**：删承接废话、合并重复要点、缩短段落。先删 no-op，再删次要内容。
3. **拆页**：一页实在装不下，拆成两页（比如「英文原文展示」+「中文解读」分两页）。

**每次改完都用 `lint_page.mjs` 验证**，别靠肉眼。

---

### 中文 codeblock 块窄、字挤（只占页面一半宽）

**现象**：codeblock 里的中文每行只显示十几个字就换行，整个米色块看起来只占页面一半宽。

**根因**：写中文 codeblock 时手动加了 `\n` 换行符，配合 CSS 的 `white-space: pre-wrap`，浏览器尊重这些手动换行——每行就显示你手写的那几个字。

**解法**：**中文 codeblock 不加手动换行**，让中文自然换行撑满 codeblock 宽度。英文 codeblock 才保留换行（英文不换行会挤成一坨）。

---

### codeblock 字号偏小（21px 等宽）

**现象**：codeblock 字明显比正文（24px 非等宽）小一档，读起来费劲。

**根因**：等宽字体视觉上显小，叠加 21px 字号，比正文小。

**解法**：如果内容允许，可在 run 目录的模板副本里把 codeblock 字号提到 22-23px。但英文原文 codeblock 字号小一点是合理的（代码感），不必强求跟正文一样大。

---

## 内容类

### 标题字符数估错（超 20 字）

**现象**：caption.md 里标的字符数跟实际不符，尤其含英文 token 的标题（`GPT-5.6` 就 7 个字符）。

**根因**：agent 对「英文字母/数字/标点各算 1」估不准。

**解法**：**用 `count_title.mjs` 数，别靠目测**：
```bash
node scripts/count_title.mjs "标题一" "标题二" "标题三"
# 或从文件：node scripts/count_title.mjs -f titles.txt
```
数完超过 20 的删掉或重写。

---

### 插图隐喻被画歪（小黑动作不对）

**现象**：生图返回了，但验证发现隐喻画歪了（要方括号画成勾选框、要汇流画成拿笔、小黑成了装饰）。

**根因**：模型对某些视觉概念有顽固误读。

**解法**：见 [IMAGE-PROMPTS.md 的「隐喻被误读」](IMAGE-PROMPTS.md#内容失败empty-url--http-400--隐喻被误读)。换隐喻载体，不要原样重发。

---

## 流程类

### 加页后页码不一致

**现象**：新增一页后，其他页的 `NUM/TOTAL` 没更新，出现封面 `00/09` 但最后一页 `10/09` 的矛盾。

**根因**：加页/删页后忘了全局更新 NUM 和 TOTAL。

**解法**：加页/删页后，**所有页的 JSON 都要重过一遍 NUM/TOTAL**。优先用 `scripts/renumber.mjs`（它同时改文件名、NUM、跨页引用，避免手写脚本的 regex 留 bug）：
```bash
# cover 从 00 改成 01，全部后移一位（dry run 先看计划，加 --apply 真写）
node <skill>/scripts/renumber.mjs 00:01,01:02,02:03,03:04,04:05,05:06,06:07,07:08,08:09 --apply
node <skill>/scripts/renumber.mjs 00:01,01:02,...,08:09 --total 09 --apply  # 同时改 TOTAL
```
然后在 shot-list.md 顶部记下页码规则（默认 cover=01），渲染前核对每页一致。

---

### 页码重排后，BODY 里写死的「第 X 页」指向错误

**现象**：页码重排后，某页正文里「按第 06 页操作」指向的内容其实是现在的第 07 页甚至第 08 页——读者跳过去扑空，或读到错的内容。

**根因**：BODY/SUMMARY/LEAD/NOTE 里的「第 X 页」是写死的字符串，不随 NUM 字段自动改。手动 grep 改遗漏一个就出错。

**解法**：页码重排必须同步改跨页引用——`scripts/renumber.mjs` 自动处理。如果你手改 NUM（没用脚本），手动查一遍所有跨页引用：
```bash
grep -n "第 [0-9]\+ 页" pages/*.json
```
没在映射里覆盖到的引用，renumber.mjs 会保留不动并打印出来方便你查。

**更稳的做法**：跨页引用优先用**章节名**（「按『现在该怎么用』那页操作」）而非页码——对页码重排免疫，读者也更容易找到对应章节。
