# 生图 prompt 模板（默认风格：小黑怪诞手绘插图）

这是每张内容页插图的生图 prompt 骨架。占位符 `{{...}}` 由 agent 按该页的认知锚点填入。
封面与结尾页**不用**此模板——它们是纯 HTML 排版 + SVG 小黑球。

**关键规则（踩过的坑，必须遵守）：**
- 背景色用**精确 hex**（如 `#FBF7EE`），并强调 "match this exact hex"。**绝不**用 cream/beige/warm/暖米 这种暖色联想词——模型一看到就往黄里渲染，"not yellow" 的否定压不住正面词。
- 小黑是 **small solid-black blob**（小球/小团块），**不是**大的人形角色（humanoid 占地方、不适合信息密度）。强调 "a blob, NOT a big humanoid"。
- 小黑身上**不要写任何文字**（模型常自作主张在角色脸上写"小黑"两字）。
- 一张图只讲**一个**核心结构；小黑必须做**核心动作**（去掉小黑隐喻就不成立 = 不合格）。
- 每张图都要**重新发明一个低科技隐喻**，不能套用别页的隐喻，也不能照搬示例。

**Prompt 复杂度上限（实测 GLM-Image 经验，必须遵守）：**
- **元素清单 ≤ 5 个**。超过 5 个不同物件时，GLM-Image 等后端常返回空 url（生成失败）。把多元素对比（如三行矩阵、多格分镜）**拆成单隐喻单画面**，或把次要元素移到卡片正文。
- **每段描述 ≤ 2 句**。整篇 prompt 总长控制在 60 行内。冗长的 composition 描述会触发后端 token 超限或内容过滤。
- **失败的信号**：`no image url in response`、HTTP 400、`fetch failed`。首生失败后**精简 prompt**（砍元素、合并段落）再重试，而不是原样重试——原样重试大概率还是失败。

---

## Prompt 骨架（填好后交给生图后端）

```
Generate one standalone 16:9 HORIZONTAL Chinese article illustration.

Visual DNA:
Light neutral background, color exactly {{BG}} — match this exact hex precisely. Minimalist black hand-drawn line art. Slightly wobbly pen lines. Lots of empty space. Sparse red/orange handwritten Chinese annotations. Clean absurd product-sketch feeling. No gradients, no shadows, no paper texture, no commercial vector style, no PPT infographic look, no cute mascot poster, no children's illustration, no realistic UI.

Recurring IP character required:
小黑, a small solid-black absurd blob creature with white dot eyes, tiny thin legs, blank serious deadpan expression. Small and compact — a blob, NOT a big humanoid. 小黑 must perform the core conceptual action, not decorate the scene. Do NOT write any Chinese characters on 小黑's body or face. Make 小黑 serious, deadpan, slightly bizarre, not cute.

Theme:
{{THEME}}

Structure type:
{{STRUCTURE}}

Core idea:
{{CORE_IDEA}}

Composition:
{{COMPOSITION}}

Suggested elements:
{{ELEMENTS}}

Chinese handwritten labels:
{{LABELS}}

Color use:
Black for main line art and 小黑. {{COLOR_RULE}}

Constraints:
One image explains only one core structure. 16:9 horizontal. Main subject around 40%-55% of canvas. Preserve at least 40% blank space. Use at most 4-5 short handwritten Chinese labels. Background color exactly {{BG}}. Do not write a title in the top-left corner. Do not write the structure type on the image. Do not write any text on 小黑. Invent a fresh low-tech visual metaphor for this specific concept. Clear but not instructional, interesting but not childish, strange but clean.
```

---

## 结构类型参考（Composition 填写时选一种）

| 结构 | 适合 | 画法要点 |
|------|------|----------|
| Workflow 流程 | 输入→处理→输出 | 左输入/中小黑处理/右输出，橙色箭头表达流向 |
| 系统局部 | 信息来源/过滤器/agent局部 | 只画 3-5 核心模块，小黑参与其中一个关键动作 |
| 前后对比 | 混乱/有序、手动/自动 | 左右两段，中间橙色箭头 |
| 角色状态 | 痛点/卡住到跑起来 | 2-4 个小状态，每个一个短标注 |
| 概念隐喻 | 工厂/黑盒/工作流机器 | 一个大怪物件，少量输入一个输出，要有记忆点 |
| 方法分层 | 框架/层级/能力栈 | 一层层盒子，不要正式金字塔 |
| 地图路线 | 从想法到上线/路径 | 一条弯曲路径，少量节点，小黑牵线或走路 |
| 过程演示 | 累积/递进/阈值 | 同一物件多个递增状态，箭头串联（如少→满→溢出） |

**隐喻要"机制自洽"**：画面的外壳必须直接体现概念机制，而不是贴个标签硬说。
反例：小黑推煤车 + 一条虚线标"140K"——煤车和"变笨"没内在关联，看不懂。
正例：小车从少→满→溢出三段——"装不下就洒了"直接演示了"多了会出错"。

## 颜色规则参考（COLOR_RULE 填写）

- 橙色 = 主路径/箭头/从 A 到 B 的流向
- 红色 = 重点/问题/结果/警戒线（只用在一处）
- 蓝色 = 补充说明/系统状态（可选，不是每张都要）
- 黑色 = 主体线稿、小黑、框线、主要文字

颜色克制，宁可少不要多。

